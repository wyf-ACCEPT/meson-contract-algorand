require('dotenv').config()
const base32Decode = require('base32-decode')
const { readFileSync, readdir } = require('fs')
const { Wallet, SigningKey, utils, recoverAddress, keccak256, assert } = require('ethers')
const { Algodv2, Indexer, OnApplicationComplete, mnemonicToSecretKey, waitForConfirmation, assignGroupID, makePaymentTxnWithSuggestedParams, makeApplicationCreateTxn, getApplicationAddress, makeApplicationCallTxnFromObject, makeApplicationOptInTxn, makeAssetTransferTxnWithSuggestedParamsFromObject } = require("algosdk")


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

        // accounts
        this.alice = this.load_mnemonic(process.env.WALLET_1)
        this.bob = this.load_mnemonic(process.env.WALLET_2)
        this.carol = this.load_mnemonic(process.env.WALLET_3)
        this.initiator_wallet = new Wallet(process.env.INITIATOR_PRIVATE_KEY)
        this.initiator_address = this.initiator_wallet.address

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
            if (typeof (obj) == 'number') arraylist.push(this.intToUint8Array(obj, 8))
            else if (typeof (obj) == 'string') arraylist.push(this.encoder.encode(obj))
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

    decode_algorand_address(algo_addr) {
        let buffer_address = new Buffer.from(base32Decode(algo_addr, 'RFC4648').slice(0, -4))
        let hex_address = buffer_address.reduce((accumulator, currentValue) => {
            return accumulator + currentValue.toString(16).padStart(2, '0')
        }, '')
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
}



main = async () => {

    const utils = new Utils()
    await utils.show_account_info()

    const transfer_to_app_amount = 400_000
    const lp_deposit_amount = 125 * 1_000_000
    const { alice, bob, carol, encoder, usdc_index, usdt_index, on_complete_param, listToUint8ArrayList, submit_transaction, submit_transaction_group, sp_func, build_encoded, get_swapID, get_expire_ts } = utils

    // returned = indexer_client.lookup_account_application_local_state(bob_address, application_id=meson_index)
    // balances_saved = returned['apps-local-states'][0]['key-value']
    // print("LP(Bob) balance:")
    // for balance in balances_saved:
    //     print("Asset %d: %d" % (int.from_bytes(de64(balance['key'])[8:], 'big'), balance['value']['uint'] / 1e6))
    // let returned = await utils.indexer.lookupAccountAppLocalStates(bob.addr).do()
    // console.log(returned)
    // console.log(await utils.indexer.lookupAccountTransactions(alice.addr).do())
    // console.log(await utils.indexer.lookupAccountAssets(alice.addr).do())
    // console.log(await utils.indexer.lookupAccountAppLocalStates(usdc_index, address=alice.addr).do())
    // console.log(await utils.indexer.makeHealthCheck().do())

    // // /indexer/javascript/AccountInfo.js
    // await utils.indexer.lookupAccountByID(alice.addr).do().catch(e => {
    //     console.log(e);
    //     console.trace();
    // });
    // curl https://testnet-idx.algonode.network:8980/v2/accounts/XIU7HGGAJ3QOTATPDSIIHPFVKMICXKHMOR2FJKHTVLII4FAOA3CYZQDLG4/apps-local-state



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


    console.log("================== 1.2 Transfer to Meson ==================")
    await submit_transaction(alice.sk, makePaymentTxnWithSuggestedParams(
        alice.addr, meson_address, transfer_to_app_amount, undefined, undefined, await sp_func()
    ))
    console.log("Transfer $ALGO to Meson app success!")
    console.log(`App ${meson_index} balance: ${await utils.client.accountInformation(meson_address).do().amount / 1e6
        } ALGO.\n`)


    console.log("================== 1.3 Add USDC and USDT ==================")
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


    console.log("================== 2.2 LP deposit to App ==================")
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

    // console.log("================== 3.1  ==================")
    // const amount_transfer = 50 * 1_000_000
    // let encoded_hexstring = build_encoded(amount_transfer, get_expire_ts(), '02', '01', false)
    // let encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
    // console.log(encoded_hexstring)

    // const initiator = '2ef8a51f8ff129dbb874a0efb021702f59c1b211'
    // let swapId = get_swapID(encoded_hexstring, initiator, false)
    // console.log(swapId)


}

main()