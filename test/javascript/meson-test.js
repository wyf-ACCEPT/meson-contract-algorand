const { dotenv } = require('dotenv')
const base32Decode = require('base32-decode')
const { readFileSync } = require('fs')
const { Wallet, keccak256, assert } = require('ethers')
const { Algodv2, Indexer, OnApplicationComplete, mnemonicToSecretKey, waitForConfirmation, assignGroupID, makePaymentTxnWithSuggestedParams, makeApplicationCreateTxn, getApplicationAddress, makeApplicationCallTxnFromObject, makeApplicationOptInTxn, makeAssetTransferTxnWithSuggestedParamsFromObject } = require("algosdk")
dotenv.config()

class Utils {
    constructor() {
        // base requirements
        this.client = new Algodv2(process.env.ALGOD_TOKEN, process.env.TESTNET_ALGOD_RPC)
        this.indexer = new Indexer(process.env.ALGOD_TOKEN, process.env.TESTNET_INDEXER_RPC, 8980)
        this.on_complete_param = OnApplicationComplete.NoOpOC
        this.usdc_index = 160363393
        this.usdt_index = 160363405
        this.request_typehash = '7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb25'
        this.release_typehash = 'd23291d9d999318ac3ed13f43ac8003d6fbd69a4b532aeec9ffad516010a208c'
        this.encoder = new TextEncoder()

        // bind functions
        this.sp_func = this.sp_func.bind(this)
        this.listToUint8ArrayList = this.listToUint8ArrayList.bind(this)
        this.submit_transaction = this.submit_transaction.bind(this)
        this.submit_transaction_group = this.submit_transaction_group.bind(this)
        this.sign_request = this.sign_request.bind(this)
        this.sign_release = this.sign_release.bind(this)
        this.show_boxes = this.show_boxes.bind(this)

        // accounts
        this.alice = this.load_mnemonic(process.env.WALLET_1)
        this.bob = this.load_mnemonic(process.env.WALLET_2)
        this.carol = this.load_mnemonic(process.env.WALLET_3)
        this.initiator_wallet = new Wallet(process.env.INITIATOR_PRIVATE_KEY)
        this.initiator_address = this.initiator_wallet.address.slice(2)
        this.initiator_buffer = Buffer.from(this.initiator_address, 'hex')

        // read contract code
        this.meson_contract_code = readFileSync(
            './contract/compiled_teal/meson.teal', { encoding: 'utf-8' }
        )
    }

    load_mnemonic(string) {
        return mnemonicToSecretKey(string.split(', ').join(' '))
    }

    intToUint8Array(num, bytes_length) {
        let buffer = new ArrayBuffer(bytes_length);
        let view = new DataView(buffer);
        for (let i = bytes_length - 1; i >= 0; i--) {
            view.setUint8(i, num & 0xff);
            num >>= 8;
        }
        return new Uint8Array(buffer);
    }

    listToUint8ArrayList(list) {
        let arraylist = []
        for (var obj of list) {
            if (typeof obj == 'number') arraylist.push(this.intToUint8Array(obj, 8))
            else if (typeof obj == 'string') arraylist.push(this.encoder.encode(obj))
            else if (Buffer.isBuffer(obj)) arraylist.push(new Uint8Array(obj))
            else throw new Error("Wrong type!")
        }
        return arraylist
    }

    get_expire_ts(delay = 90) {
        return Math.floor(Date.now() / 1e3 + 60 * delay)
    }

    build_encoded(amount, expireTs, outToken, inToken, return_bytes = true,
        salt = 'c00000000000e7552620', fee = '0000000000') {
        let version = '01'
        let amount_string = amount.toString(16).padStart(10, '0')
        let expireTs_string = expireTs.toString(16).padStart(10, '0')
        let outChain = '011b'
        let inChain = '011b'
        let encoded_hexstring = [version, amount_string, salt, fee, expireTs_string, outChain, outToken, inChain, inToken].join('')
        let encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
        assert(amount < 0x0fffffffff, "Amount should less than $68719.476735!")
        assert(encoded_hexstring.length == 64, "Encodedswap length should be 64!")
        if (return_bytes) return encoded_bytes
        else return encoded_hexstring
    }

    get_swapID(encoded_hexstring, initiator, return_bytes = true) {
        let concat = encoded_hexstring + initiator
        assert(concat.length == 104 && typeof (concat) == 'string', "")
        let hash_hexstring = keccak256(Buffer.from(concat, 'hex')).slice(2)
        let hash_bytes = Buffer.from(hash_hexstring, 'hex')
        if (return_bytes) return hash_bytes
        else return hash_hexstring
    }

    buffer_to_hex(buffer) {
        return buffer.reduce((accumulator, currentValue) => {
            return accumulator + currentValue.toString(16).padStart(2, '0')
        }, '')
    }

    hex_timestamp_to_date(timestamp_hex) {
        if (timestamp_hex == '1111111111') return '[Closed]'
        return new Date(parseInt(timestamp_hex, 16) * 1e3)
    }

    decode_algorand_address(algo_addr) {
        let buffer_address = new Buffer.from(base32Decode(algo_addr, 'RFC4648').slice(0, -4))
        let hex_address = this.buffer_to_hex(buffer_address)
        return hex_address
    }

    sign_request(encoded_hexstring) {
        let content_hash = keccak256(Buffer.from(encoded_hexstring, 'hex')).slice(2)
        let digest_request = Buffer.from(keccak256(
            Buffer.from(this.request_typehash + content_hash, 'hex')
        ).slice(2), 'hex')
        let sig = this.initiator_wallet.signingKey.sign(digest_request)
        return [Buffer.from(sig.r.slice(2), 'hex'), Buffer.from(sig.s.slice(2), 'hex'), sig.v - 27]
    }

    sign_release(encoded_hexstring, recipient_algo_addr) {
        let recipient_addr = this.decode_algorand_address(recipient_algo_addr)
        let content_hash = keccak256(Buffer.from(encoded_hexstring + recipient_addr, 'hex')).slice(2)
        let digest_release = Buffer.from(keccak256(
            Buffer.from(this.release_typehash + content_hash, 'hex')
        ).slice(2), 'hex')
        let sig = this.initiator_wallet.signingKey.sign(digest_release)
        return [Buffer.from(sig.r.slice(2), 'hex'), Buffer.from(sig.s.slice(2), 'hex'), sig.v - 27]
    }

    async sp_func() {
        return await this.client.getTransactionParams().do()
    }

    async show_account_info() {
        console.log("========================== Account Balance Info ==========================")
        let info = await this.client.accountInformation(this.alice.addr).do()
        console.log(`Alice ${info.address} balance: ${info.amount / 1e6}`)
        info = await this.client.accountInformation(this.bob.addr).do()
        console.log(`Bob   ${info.address} balance: ${info.amount / 1e6}`)
        info = await this.client.accountInformation(this.carol.addr).do()
        console.log(`Carol ${info.address} balance: ${info.amount / 1e6}\n`)
    }

    async submit_transaction(private_key, unsigned_txn) {
        let signed_txn = unsigned_txn.signTxn(private_key)
        let txId = unsigned_txn.txID().toString()
        await this.client.sendRawTransaction(signed_txn).do()
        console.log(`Signed transaction with txID: ${txId}`)
        let confirmedTxn = await waitForConfirmation(this.client, txId, 2)
        console.log(`Confirmed on round ${confirmedTxn["confirmed-round"]}!\n`)
        let response = await this.client.pendingTransactionInformation(txId).do()
        return response
    }

    async submit_transaction_group(private_key, unsigned_txns) {
        assignGroupID(unsigned_txns)
        let signed_txns = []
        for (var txn of unsigned_txns) {
            signed_txns.push(txn.signTxn(private_key))
        }
        let { txId } = await this.client.sendRawTransaction(signed_txns).do();
        console.log(`Signed transaction with txID: ${txId}`)
        let confirmedTxn = await waitForConfirmation(this.client, txId, 2)
        console.log(`Confirmed on round ${confirmedTxn["confirmed-round"]}!\n`)
        let response = await this.client.pendingTransactionInformation(txId).do()
        return response
    }

    async compile_program(source_code) {
        let compile_response = await this.client.compile(this.encoder.encode(source_code)).do()
        return new Uint8Array(Buffer.from(compile_response.result, "base64"))
    }

    async show_boxes(meson_index, is_in_chain) {
        if (is_in_chain == true) {
            console.log("Meson App boxes (encodedSwap -> postedValue): ")
            let box_res = await this.client.getApplicationBoxes(meson_index).do()
            for (let box of box_res.boxes) {
                let encoded_key = box.name
                let posted_value = (await this.client.getApplicationBoxByName(meson_index, encoded_key).do()).value
                if (posted_value.length == 84)
                    console.log(
                        `[EncodedSwap] %s, \n\t-> [PostedValue] (lp, initiator, from_address): \n\t\t\t(%s, \n\t\t\t%s, \n\t\t\t%s)`,
                        this.buffer_to_hex(encoded_key),
                        this.buffer_to_hex(posted_value.slice(0, 32)),
                        this.buffer_to_hex(posted_value.slice(32, 52)),
                        this.buffer_to_hex(posted_value.slice(52)),
                    )
            }
        } else {
            console.log("Meson App boxes (swapId -> lockedValue): ")
            let box_res = await this.client.getApplicationBoxes(meson_index).do()
            for (let box of box_res.boxes) {
                let swapid_key = box.name
                let locked_value = (await this.client.getApplicationBoxByName(meson_index, swapid_key).do()).value
                if (locked_value.length == 69)
                    console.log(
                        `[SwapID] %s, \n\t-> [LockedValue] (lp, until, recipient): \n\t\t\t(%s, \n\t\t\t%s, \n\t\t\t%s)`,
                        this.buffer_to_hex(swapid_key),
                        this.buffer_to_hex(locked_value.slice(0, 32)),
                        this.hex_timestamp_to_date(this.buffer_to_hex(locked_value.slice(32, 37))),
                        this.buffer_to_hex(locked_value.slice(37)),
                    )
            }
        }
    }
}



main = async () => {

    const utils = new Utils()
    await utils.show_account_info()

    const transfer_to_app_amount = 400_000
    const lp_deposit_amount = 125 * 1_000_000
    const { alice, bob, carol, usdc_index, usdt_index, on_complete_param, initiator_buffer, initiator_address, listToUint8ArrayList, submit_transaction, submit_transaction_group, sp_func, build_encoded, get_swapID, get_expire_ts, sign_request, sign_release, show_boxes } = utils




    // --------------------------------------------------------------------------------------------
    console.log("\n# 1 Create App #")

    console.log("================== 1.1 Create Meson App ==================")
    let blank_program = await utils.compile_program('#pragma version 8\nint 1\nreturn')
    let meson_program = await utils.compile_program(utils.meson_contract_code)

    let create_app_tx = await submit_transaction(alice.sk, makeApplicationCreateTxn(
        alice.addr, await sp_func(), on_complete_param, meson_program, blank_program,
        6, 0, 12, 0, undefined, undefined, undefined, undefined, undefined, undefined,
        undefined, 1, undefined
    ))
    let meson_index = create_app_tx['application-index']
    let meson_address = getApplicationAddress(meson_index)
    console.log(`Create Meson Contract success! App id: ${meson_index}, App Address: ${meson_address}\n`)


    console.log("\n================== 1.2 Transfer to Meson ==================")
    await submit_transaction(alice.sk, makePaymentTxnWithSuggestedParams(
        alice.addr, meson_address, transfer_to_app_amount, undefined, undefined, await sp_func()
    ))
    console.log("Transfer $ALGO to Meson app success!")
    console.log(`App ${meson_index} balance: ${(await utils.client.accountInformation(meson_address).do()).amount / 1e6} ALGO.\n`)


    console.log("\n================== 1.3 Add USDC and USDT ==================")
    await submit_transaction(alice.sk, makeApplicationCallTxnFromObject({
        from: alice.addr,
        suggestedParams: await sp_func(),
        appIndex: meson_index,
        onComplete: on_complete_param,
        appArgs: listToUint8ArrayList(['addSupportToken', 1]),
        foreignAssets: [usdc_index],
    }))
    console.log("Meson App Optin USDC success!\n")
    await submit_transaction(alice.sk, makeApplicationCallTxnFromObject({
        from: alice.addr,
        suggestedParams: await sp_func(),
        appIndex: meson_index,
        onComplete: on_complete_param,
        appArgs: listToUint8ArrayList(['addSupportToken', 2]),
        foreignAssets: [usdt_index],
    }))
    console.log("Meson App Optin USDT success!\n")




    // --------------------------------------------------------------------------------------------
    console.log("\n# 2 LP deposit #")

    console.log("================== 2.1 LP Opt in App ==================")
    await submit_transaction(bob.sk, makeApplicationOptInTxn(
        bob.addr, await sp_func(), meson_index,
    ))
    console.log("LP(Bob) opt in Meson App success!\n")


    console.log("\n================== 2.2 LP deposit to App ==================")
    await submit_transaction_group(bob.sk, [
        makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['deposit', lp_deposit_amount]),
            foreignAssets: [usdc_index]
        }),
        makeAssetTransferTxnWithSuggestedParamsFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            to: meson_address,
            amount: lp_deposit_amount,
            assetIndex: usdc_index,
        })
    ],)
    console.log(`LP(Bob) deposit ${lp_deposit_amount / 1e6} mUSDC into Meson App!\n`)

    await submit_transaction_group(bob.sk, [
        makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['deposit', lp_deposit_amount]),
            foreignAssets: [usdt_index]
        }),
        makeAssetTransferTxnWithSuggestedParamsFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            to: meson_address,
            amount: lp_deposit_amount,
            assetIndex: usdt_index,
        })
    ],)
    console.log(`LP(Bob) deposit ${lp_deposit_amount / 1e6} mUSDT into Meson App!`)
    console.log("[TODO] Cannot use indexer to see local state correctly!\n")




    // --------------------------------------------------------------------------------------------
    console.log("\n# 3 Swap! #")

    console.log("================== 3.0 Init ==================")

    // let meson_index = 162573802                                 // if needed
    // let meson_address = getApplicationAddress(meson_index)      // if needed

    const amount_swap = 3 * 1_000_000
    const encoded_hexstring = build_encoded(amount_swap, get_expire_ts(), '02', '01', false)
    const encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
    console.log(`EncodedSwap: ${encoded_hexstring}`)


    console.log("\n\n================== 3.1 PostSwap & BondSwap ==================")

    let [r, s, v] = sign_request(encoded_hexstring)
    console.log("Complete request signing!")

    let postSwap_group = [
        makeApplicationCallTxnFromObject({
            from: carol.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['postSwap', encoded_bytes, r, s, v, initiator_buffer]),
            boxes: [{
                appIndex: meson_index,
                name: new Uint8Array(encoded_bytes),
            }],
        }),
        makeAssetTransferTxnWithSuggestedParamsFromObject({
            from: carol.addr,
            suggestedParams: await sp_func(),
            to: meson_address,
            amount: amount_swap,
            assetIndex: usdc_index,
        }),
    ]
    for (let pad_index = 0; pad_index < 7; pad_index++)
        postSwap_group.push(makeApplicationCallTxnFromObject({
            from: carol.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['padding', pad_index]),
        }))
    await submit_transaction_group(carol.sk, postSwap_group)
    console.log("Step 1.1. User(Carol) posted swap success!\n")

    await submit_transaction(bob.sk, makeApplicationCallTxnFromObject({
        from: bob.addr,
        suggestedParams: await sp_func(),
        appIndex: meson_index,
        onComplete: on_complete_param,
        appArgs: listToUint8ArrayList(['bondSwap', encoded_bytes]),
        boxes: [{
            appIndex: meson_index,
            name: new Uint8Array(encoded_bytes),
        }],
    }))
    console.log("Step 1.2. LP(Bob) Bonded swap success!\n")
    await show_boxes(meson_index, true)


    console.log("\n\n================== 3.2 Lock ==================")

    let lock_group = [
        makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['lock', encoded_bytes, r, s, v, initiator_buffer]),
            accounts: [carol.addr],
            boxes: [{
                appIndex: meson_index,
                name: new Uint8Array(get_swapID(encoded_hexstring, initiator_address)),
            }],
        }),
    ]
    for (let pad_index = 0; pad_index < 8; pad_index++)
        lock_group.push(makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['padding', pad_index]),
        }))
    await submit_transaction_group(bob.sk, lock_group)
    console.log("Step 2. LP(Bob) lock assets success!\n")
    await show_boxes(meson_index, false)


    console.log("\n\n================== 3.3 Release ==================")

    let [r2, s2, v2] = sign_release(encoded_hexstring, carol.addr)
    console.log("Complete release signing!")

    let release_group = [
        makeApplicationCallTxnFromObject({
            from: carol.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['release', encoded_bytes, r2, s2, v2, initiator_buffer]),
            foreignAssets: [usdt_index],
            boxes: [{
                appIndex: meson_index,
                name: new Uint8Array(get_swapID(encoded_hexstring, initiator_address)),
            }],
        }),
    ]
    for (let pad_index = 0; pad_index < 8; pad_index++)
        release_group.push(makeApplicationCallTxnFromObject({
            from: carol.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['padding', pad_index]),
        }))
    await submit_transaction_group(carol.sk, release_group)
    console.log("Step 3. User(Carol) release assets success!\n")
    await show_boxes(meson_index, false)


    console.log("\n\n================== 3.4 ExecuteSwap ==================")

    let executeSwap_group = [
        makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['executeSwap', encoded_bytes, r2, s2, v2, 1]),
            accounts: [carol.addr],
            foreignAssets: [usdc_index],
            boxes: [{
                appIndex: meson_index,
                name: new Uint8Array(encoded_bytes),
            }],
        }),
    ]
    for (let pad_index = 0; pad_index < 7; pad_index++)
        executeSwap_group.push(makeApplicationCallTxnFromObject({
            from: bob.addr,
            suggestedParams: await sp_func(),
            appIndex: meson_index,
            onComplete: on_complete_param,
            appArgs: listToUint8ArrayList(['padding', pad_index]),
        }))
    await submit_transaction_group(bob.sk, executeSwap_group)
    console.log("Step 4. LP(Bob) executeSwap success!\n")
    await show_boxes(meson_index, true)

}

main()