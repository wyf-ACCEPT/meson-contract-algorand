import base64
from pyteal import compileTeal, Mode, Return, Int
from algosdk import account, mnemonic, logic
from algosdk.v2client import algod
from algosdk.future import transaction


class TealApp:
    
    def __init__(self) -> None:
        TESTNET_ALGOD_RPC = "https://testnet-api.algonode.network"
        ALGOD_TOKEN = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        mnemonic_1 = open("../wallet_1").read().replace(',', ' ')
        self.algod_client = algod.AlgodClient(ALGOD_TOKEN, TESTNET_ALGOD_RPC)
        self.sp_func = self.algod_client.suggested_params
        self.on_complete_param = transaction.OnComplete.NoOpOC
        self.alice_private_key = mnemonic.to_private_key(mnemonic_1)
        self.alice_address = account.address_from_private_key(self.alice_private_key)
    
    
    def submit_transaction(self, private_key: str, unsigned_txn: transaction.Transaction):
        signed_txn = unsigned_txn.sign(private_key)
        txid = self.algod_client.send_transaction(signed_txn)
        print("Signed transaction with txID: {}".format(txid))
        confirmed_txn = transaction.wait_for_confirmation(self.algod_client, txid, 3)
        print("Confirmed on round {}!".format(confirmed_txn['confirmed-round']))
        transaction_response = self.algod_client.pending_transaction_info(txid)
        return transaction_response


    def compile_program(self, source_code):
        compile_response = self.algod_client.compile(source_code)
        return base64.b64decode(compile_response['result'])


    def create_app(self, program_func, write_to_file='', stateschema=[5, 5, 0, 0]):
        main_program = self.compile_program(teal_sentences := compileTeal(
            program_func(), Mode.Application, version=8
        ))
        blank_program = self.compile_program(compileTeal(
            Return(Int(1)), Mode.Application, version=8
        ))
        if write_to_file:
            open('./compiled_teal/%s' % write_to_file, 'w').write(teal_sentences)

        create_app_tx = self.submit_transaction(
            self.alice_private_key, 
            transaction.ApplicationCreateTxn(
                self.alice_address, 
                self.sp_func(), 
                self.on_complete_param, 
                main_program, 
                blank_program,
                transaction.StateSchema(stateschema[0], stateschema[1]), 
                transaction.StateSchema(stateschema[2], stateschema[3])
            )
        )
        self.application_index = create_app_tx['application-index']
        self.application_address = logic.get_application_address(self.application_index)
        print("Create app success! App id: %s; App address: %s" % 
              (self.application_index, self.application_address))
    
    
    def call_app(self, app_args=[], **kargs):
        self.submit_transaction(
            self.alice_private_key,
            transaction.ApplicationCallTxn(
                self.alice_address,
                self.sp_func(),
                self.application_index,
                self.on_complete_param,
                app_args=app_args,
                **kargs
            )
        )
