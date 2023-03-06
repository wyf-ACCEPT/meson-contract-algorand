require('dotenv').config()
const { Algodv2, OnApplicationComplete, mnemonicToSecretKey, waitForConfirmation, makePaymentTxnWithSuggestedParamsFromObject, assignGroupID } = require("algosdk")
const { Transaction } = require('algosdk/dist/types/client/v2/indexer/models/types')

class Utils {
    constructor() {
        // base requirements
        this.client = new Algodv2(process.env.ALGOD_TOKEN, process.env.TESTNET_ALGOD_RPC)
        this.on_complete_param = OnApplicationComplete.NoOpOC

        // accounts
        this.alice = this.load_mnemonic(process.env.WALLET_1)
        this.bob = this.load_mnemonic(process.env.WALLET_2)
        this.carol = this.load_mnemonic(process.env.WALLET_3)
    }

    load_mnemonic(string) {
        return mnemonicToSecretKey(string.split(', ').join(' '))
    }

    async sp_func() {
        return await this.client.getTransactionParams().do()
    }

    async show_account_info() {
        console.log("============================== Init ==============================")
        let info = await this.client.accountInformation(this.alice.addr).do()
        console.log(`Alice ${info.address} balance: ${info.amount / 1e6}`)
        info = await this.client.accountInformation(this.bob.addr).do()
        console.log(`Bob   ${info.address} balance: ${info.amount / 1e6}`)
        info = await this.client.accountInformation(this.carol.addr).do()
        console.log(`Carol ${info.address} balance: ${info.amount / 1e6}`)
        console.log()
    }

    async submit_transaction(private_key, unsigned_txn) {
        let signed_txn = unsigned_txn.signTxn(private_key)
        let txId = unsigned_txn.txID().toString()
        await this.client.sendRawTransaction(signed_txn).do()
        console.log(`Signed transaction with txID: ${txId}`)
        let confirmedTxn = await waitForConfirmation(this.client, txId, 2)
        console.log(`Confirmed on round ${confirmedTxn["confirmed-round"]}!\n`)
        let response = this.client.pendingTransactionInformation(txId)
        return response
    }
    // gid = transaction.calculate_group_id(unsigned_txns)
    // signed_txns = []
    // for unsigned in unsigned_txns:
    //     unsigned.group = gid
    //     signed = unsigned.sign(private_key)
    //     signed_txns.append(signed)
    // gtxid = algod_client.send_transactions(signed_txns)
    // print("Signed transaction group with gtxID: {}".format(gtxid))
    // confirmed_txn = transaction.wait_for_confirmation(algod_client, gtxid, 3)
    // print("Confirmed on round {}!".format(confirmed_txn['confirmed-round']))
    // transaction_response = algod_client.pending_transaction_info(gtxid)
    // return transaction_response

    async submit_transaction_group(private_key, unsigned_txns) {
        assignGroupID(unsigned_txns)
        let signed_txns = []
        for (var txn of unsigned_txns) {
            txn.signTxn(private_key)
            signed_txns.push(txn)
        }
        let { txId } = await client.sendRawTransaction().do();
        console.log(`Signed transaction with txID: ${txId}`)
        let confirmedTxn = await waitForConfirmation(this.client, txId, 2)
        console.log(`Confirmed on round ${confirmedTxn["confirmed-round"]}!\n`)

    }

}


main = async () => {

    const utils = new Utils()
    await utils.show_account_info()

    await utils.submit_transaction(utils.alice.sk, makePaymentTxnWithSuggestedParamsFromObject({
        from: utils.alice.addr,
        to: utils.carol.addr,
        amount: 40_000,
        suggestedParams: await utils.sp_func()
    }))

    await utils.show_account_info()
}

main()