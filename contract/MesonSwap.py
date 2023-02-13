from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


# Step 1.1: Different to the one in solidity, this `postSwap` can only called by user!
def postSwap(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    postingValue: Bytes,
) -> Int:
    inChain = itemFrom('inChain', encodedSwap)
    version = itemFrom('version', encodedSwap)
    amount = itemFrom('amount', encodedSwap)
    delta = itemFrom('expireTs', encodedSwap) - Txn.first_valid_time()
    initiator = itemFromPosted('initiator', postingValue)
    lp_not_bonded = itemFromPosted('lp', postingValue)
    enumIndexIn = itemFrom('inToken', encodedSwap)
    tokenIndexIn = getTokenIndex(enumIndexIn)
    
    conditions = And(
        inChain == cp.SHORT_COIN_TYPE,
        version == cp.MESON_PROTOCOL_VERSION,
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
        lp_not_bonded == cp.ZERO_ADDRESS,
        checkRequestSignature(encodedSwap, r_s, v, initiator),
        validateTokenReceived(
            Int(1), tokenIndexIn, amount, enumIndexIn
        ),  # the user must call `AssetTransfer` at Gtxn[1], and call `postSwap` at Gtxn[0]
    )
    
    return Seq(
        Assert(conditions),
        Assert(App.box_create(encodedSwap, Int(65))),
        App.box_put(encodedSwap, postingValue),
        Approve()
    )


# Step 1.2: After user called `postSwap`, the lp should call `bondSwap`.
def bondSwap(encodedSwap: Bytes):
    return Seq(
        postedSwap_get := App.box_get(encodedSwap),
        Assert(postedSwap_get.hasValue()),
        Assert(itemFromPosted('lp', postedSwap_get.value()) == cp.ZERO_ADDRESS),
        App.box_replace(encodedSwap, Int(32), Txn.sender()),
        Approve()
    )
    


# -------------------------------------- For Test --------------------------------------
if __name__ == '__main__':
    
    def mesonswap_program_func():
        return Cond(
            [Txn.application_id() == Int(0), Approve()],
            [
                Txn.on_completion() == OnComplete.NoOp,
                Cond([
                    Txn.application_args[0] == Bytes("postSwap"),
                    postSwap(
                        Txn.application_args[1], 
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Txn.application_args[4],
                    )
                ], [
                    Txn.application_args[0] == Bytes("bondSwap"),
                    bondSwap(Txn.application_args[1]),
                ])
            ]
        )
    
    from test_run import TealApp
    ta = TealApp()
    ta.create_app(mesonswap_program_func, 'mesonswap.teal', [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 0x183301, 3])