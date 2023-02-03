from pyteal import *


# Directly using global index to map:
def addSupportToken(tokenIndex: Bytes, enumIndex: Bytes) -> Int:
    # todo: onlyDeployer
    
    #   Bytes('TokenIndex:17207135') -> Int(1)
    #   Bytes('EnumIndex:1') -> Int(17207135)
    return Seq(
        Assert(Btoi(enumIndex) != Int(0)),
        Assert(Btoi(tokenIndex) != Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex)) == Int(0)),
        Assert(App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex)) == Int(0)),
        App.globalPut(wrapTokenKeyName('EnumIndex:', enumIndex), tokenIndex),
        App.globalPut(wrapTokenKeyName('TokenIndex:', tokenIndex), enumIndex),
        Approve()
    )
    
    
def wrapTokenKeyName(suffix: str, index: Bytes) -> Bytes:
    return Concat(Bytes(suffix), index)


def getEnumIndex(tokenIndex: Bytes):
    return App.globalGet(wrapTokenKeyName('TokenIndex:', tokenIndex))


def getTokenIndex(enumIndex: Bytes):
    return App.globalGet(wrapTokenKeyName('EnumIndex:', enumIndex))


# getSupportedTokens: View explorer directly to get supported token list!



# -------------------------------------- For Test --------------------------------------
if __name__ == '__main__':
    
    def mesontoken_program_func():
        return Cond(
            [Txn.application_id() == Int(0), Approve()],
            [
                Txn.on_completion() == OnComplete.NoOp,
                Cond([
                    Txn.application_args[0] == Bytes("addSupportToken"),
                    addSupportToken(
                        Txn.application_args[1], Txn.application_args[2]
                    )
                ])
            ]
        )
    
    import base64
    from algosdk import account, mnemonic, logic
    from algosdk.v2client import algod
    from algosdk.future import transaction
    
    TESTNET_ALGOD_RPC = "https://testnet-api.algonode.network"
    ALGOD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    algod_client = algod.AlgodClient(ALGOD_TOKEN, TESTNET_ALGOD_RPC)
    sp_func = algod_client.suggested_params
    on_complete_param = transaction.OnComplete.NoOpOC
    
    def compile_program(client, source_code):
        compile_response = client.compile(source_code)
        return base64.b64decode(compile_response['result'])

    def submit_transaction(private_key: str, unsigned_txn: transaction.Transaction):
        signed_txn = unsigned_txn.sign(private_key)
        txid = algod_client.send_transaction(signed_txn)
        print("Signed transaction with txID: {}".format(txid))
        confirmed_txn = transaction.wait_for_confirmation(algod_client, txid, 3)
        print("Confirmed on round {}!".format(confirmed_txn['confirmed-round']))
        transaction_response = algod_client.pending_transaction_info(txid)
        return transaction_response
    
    mesontoken_program = compile_program(algod_client, teal_sentences := compileTeal(
        mesontoken_program_func(), Mode.Application, version=8
    ))
    blank_program = compile_program(algod_client, compileTeal(
        Return(Int(1)), Mode.Application, version=8
    ))

    mnemonic_1 = open("../wallet_1").read().replace(',', ' ')

    alice_private_key = mnemonic.to_private_key(mnemonic_1)
    alice_address = account.address_from_private_key(alice_private_key)
    
    create_app_tx = submit_transaction(alice_private_key, transaction.ApplicationCreateTxn(
        alice_address, sp_func(), on_complete_param, mesontoken_program, blank_program,
        transaction.StateSchema(5, 5), transaction.StateSchema(0, 0)
    ))
    print("Create app success! Application id:", (application_index := create_app_tx['application-index']))
    application_address = logic.get_application_address(application_index)
    
    submit_transaction(
        alice_private_key,
        transaction.ApplicationCallTxn(
            alice_address,
            sp_func(),
            application_index,
            on_complete_param,
            app_args=['addSupportToken', 154401396, 1],
        ),
    )
    
    submit_transaction(
        alice_private_key,
        transaction.ApplicationCallTxn(
            alice_address,
            sp_func(),
            application_index,
            on_complete_param,
            app_args=['addSupportToken', 0x183301, 3],
        ),
    )
    