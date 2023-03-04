from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initMesonSwap() -> Int:
    return Approve()


# Step 1.1: Different to the one in solidity, this `postSwap` can only called by user!
def postSwap(
    encodedSwap: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
    initiator: Bytes,   # This is an etheruem address
) -> Int:
    inChain = decodeSwap("inChain", encodedSwap)
    version = decodeSwap("version", encodedSwap)
    amount = decodeSwap("amount", encodedSwap)
    delta = decodeSwap("expireTs", encodedSwap) - Txn.first_valid_time()
    from_address = Txn.sender()  # TODO
    lp_not_bonded = cp.ZERO_ADDRESS
    tokenIndexIn = decodeSwap("inToken", encodedSwap)
    assetIdIn = getAssetId(tokenIndexIn)
    postingValue = postedSwapFrom(lp_not_bonded, initiator, from_address)

    conditions = And(
        version == cp.MESON_PROTOCOL_VERSION,
        inChain == cp.SHORT_COIN_TYPE,
        # TODO: check encodedSwap length = 32
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
        checkRequestSignature(encodedSwap, r, s, v, initiator),
        validateTokenReceived(
            Int(1), assetIdIn, amount, tokenIndexIn
        ),  # the user must call `AssetTransfer` at Gtxn[1], and call `postSwap` at Gtxn[0]
    )

    return Seq(
        Assert(conditions),
        Assert(App.box_create(encodedSwap, Int(84))),
        App.box_put(encodedSwap, postingValue),
        Approve(),
    )


# Step 1.2: After user called `postSwap`, the lp should call `bondSwap`.
def bondSwap(encodedSwap: Bytes) -> Int:
    return Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        Assert(itemFromPosted("lp", postedSwap_get.value()) == cp.ZERO_ADDRESS),
        App.box_replace(encodedSwap, Int(0), Txn.sender()),
        Approve(),
    )


# Step [extra].
def cancelSwap(encodedSwap: Bytes) -> Int:
    expireTs = decodeSwap("expireTs", encodedSwap)
    amount = decodeSwap("amount", encodedSwap)
    tokenIndexIn = decodeSwap("inToken", encodedSwap)
    assetIdIn = getAssetId(tokenIndexIn)
    postedSwap = ScratchVar(TealType.bytes)
    initiator = itemFromPosted("initiator", postedSwap.load())

    postedSwap_value = Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        postedSwap_get.value(),
    )
    conditions = And(
        postedSwap.load() != cp.POSTED_SWAP_EXPIRE,
        expireTs < Txn.first_valid_time(),
        App.box_delete(encodedSwap),
    )
    
    return Seq(
        postedSwap.store(postedSwap_value),
        Assert(conditions),
        safeTransfer(assetIdIn, initiator, amount, tokenIndexIn),
        Approve(),
    )


# Step 4.
def executeSwap(
    encodedSwap: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
    depositToPool: Int,
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    expireTs = decodeSwap("expireTs", encodedSwap)
    amount = decodeSwap("amount", encodedSwap)
    tokenIndexIn = decodeSwap("inToken", encodedSwap)
    assetIdIn = getAssetId(tokenIndexIn)
    postedSwap = ScratchVar(TealType.bytes)
    initiator = itemFromPosted("initiator", postedSwap.load())
    lp = itemFromPosted("lp", postedSwap.load())

    postedSwap_value = Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        postedSwap_get.value(),
    )
    conditions = And(
        postedSwap.load() != cp.POSTED_SWAP_EXPIRE,
        checkReleaseSignature(encodedSwap, recipient, r, s, v, initiator),
    )

    return Seq(
        postedSwap.store(postedSwap_value),
        Assert(conditions),
        If(
            expireTs < Txn.first_valid_time() + cp.MIN_BOND_TIME_PERIOD,
            Assert(App.box_delete(encodedSwap)),
            App.box_put(encodedSwap, cp.POSTED_SWAP_EXPIRE),
        ),
        If(
            depositToPool,
            updateBalanceOfPool(lp, assetIdIn, poolTokenBalance(lp, tokenIndexIn) + amount),
            safeTransfer(assetIdIn, lp, amount, tokenIndexIn),
        ),
        Approve(),
    )



# ------------------------------------ Main Program of Swap ------------------------------------
def mesonSwapMainFunc():
    return Cond(
        [
            Txn.application_id() == Int(0),
            initMesonSwap(),
        ],
        [
            Txn.on_completion() == OnComplete.OptIn, Approve()
        ],
        [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
                Txn.on_completion() == OnComplete.DeleteApplication,  # TODO
            ),
            Reject(),
        ],
        [
            Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [
                    Txn.application_args[0] == Bytes("addSupportToken"),
                    addSupportToken(
                        Txn.assets[0],
                        Btoi(Txn.application_args[1]),
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("postSwap"),
                    postSwap(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Txn.application_args[5],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("bondSwap"),
                    bondSwap(Txn.application_args[1]),
                ],
                [
                    Txn.application_args[0] == Bytes("cancelSwap"),
                    cancelSwap(Txn.application_args[1]),
                ],
                [
                    Txn.application_args[0] == Bytes("executeSwap"),
                    executeSwap(
                        Txn.application_args[1],
                        Txn.application_args[2],
                        Txn.application_args[3],
                        Btoi(Txn.application_args[4]),
                        Btoi(Txn.application_args[5]),
                        Txn.accounts[1],
                    ),
                ],
                [
                    Txn.application_args[0] == Bytes("padding"),
                    Approve()
                ],
            ),
        ],
    )



# -------------------------------------- For Test --------------------------------------
if __name__ == "__main__":
    from test_run import TealApp
    from algosdk.future import transaction
    from Crypto.Hash import keccak
    from web3.auto import w3
    import time

    ta = TealApp()
    open("./contract/compiled_teal/%s" % "mesonswap.teal", "w").write(
        compileTeal(mesonSwapMainFunc(), Mode.Application, version=8)
    )
    
    def get_expire_ts(delay=90):   # default to 90 minutes
        return int(time.time()) + 60*delay

    def build_encoded(amount: int, expireTs: int, outToken, inToken, 
                    salt='c00000000000e7552620', fee='0000000000', return_bytes=True):
        assert amount < 0x1111111111
        version = '01'
        amount_string = hex(amount)[2:].rjust(10, '0')
        expireTs_string = hex(expireTs)[2:].rjust(10, '0')
        outChain = '011b'
        inChain = '011b'
        encoded_string = ''.join([
            '0x', version, amount_string, salt, fee, expireTs_string, outChain, outToken, inChain, inToken
        ])
        return bytes.fromhex(encoded_string[2:]) if return_bytes else encoded_string

    def keccak256(bytes_str):
        keccak_func = keccak.new(digest_bits=256)
        hash_value = keccak_func.update(bytes.fromhex(bytes_str) if type(bytes_str) == str else bytes_str)
        return hash_value.hexdigest()

    request_type = "bytes32 Sign to request a swap on Meson (Testnet)"
    release_type = "bytes32 Sign to release a swap on Meson (Testnet)address Recipient"
    request_typehash = bytes.fromhex('7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb25')
    release_typehash = bytes.fromhex('d23291d9d999318ac3ed13f43ac8003d6fbd69a4b532aeec9ffad516010a208c')

    amount_transfer = 50 * 1_000_000
    phil_private_key = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    initiator = phil_address = bytes.fromhex('2ef8a51f8ff129dbb874a0efb021702f59c1b211')
    encodedSwap = build_encoded(amount_transfer, get_expire_ts(), '02', '01')
        
    digest_request = bytes.fromhex(keccak256(request_typehash + bytes.fromhex(keccak256(encodedSwap))))
    signed_message = w3.eth.account._sign_hash(digest_request, phil_private_key)
    r_int, s_int, v = signed_message.r, signed_message.s, signed_message.v - 27
    r, s = int.to_bytes(r_int, 32, 'big'), int.to_bytes(s_int, 32, 'big')
    
    usdc_index = 160363393
    usdt_index = 160363405
    
    on_complete_param = transaction.OnComplete.NoOpOC
    
    ta.create_app(mesonSwapMainFunc, 'mesonswap.teal', [12, 12, 0, 0])
    
    ta.submit_transaction('', transaction.PaymentTxn(
        ta.alice_address, ta.sp_func(), ta.application_address, 400_000,
    ))
    ta.submit_transaction('', transaction.ApplicationCallTxn(
        ta.alice_address, ta.sp_func(), ta.application_index, on_complete_param,
        app_args=['addSupportToken', 1], foreign_assets=[usdc_index]
    ))
    print("Meson App Optin USDC success!\n")
    ta.submit_transaction('', transaction.ApplicationCallTxn(
        ta.alice_address, ta.sp_func(), ta.application_index, on_complete_param,
        app_args=['addSupportToken', 2], foreign_assets=[usdt_index]
    ))
    print("Meson App Optin USDT success!\n")
    
    # ta.call_app(['optIn'])
    meson_index = ta.application_index
    meson_address = ta.application_address
    ta.submit_transaction_group('', [
    transaction.ApplicationCallTxn(
        ta.alice_address, ta.sp_func(), meson_index, on_complete_param,
        app_args=['postSwap', encodedSwap, r, s, v, initiator],
        boxes=[(meson_index, encodedSwap)]
    ),
    transaction.AssetTransferTxn(
        ta.alice_address, ta.sp_func(), meson_address, amount_transfer, usdc_index
    ),
    *[transaction.ApplicationCallTxn(
        ta.alice_address, ta.sp_func(), meson_index, on_complete_param,
        app_args=['padding', padding_num]
    ) for padding_num in range(7)],
])
