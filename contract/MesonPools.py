from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def depositAndRegister(
    amount: Int,
    tokenIndex: Int,
) -> Int:
    lp = Txn.sender()
    enumIndex = getEnumIndex(tokenIndex)
    
    conditions = And(
        validateTokenReceived(Int(1), tokenIndex, amount, enumIndex),
        poolTokenBalance(lp, enumIndex) == Int(0),
    )
    
    return Seq(
        Assert(conditions),
        App.localPut(lp, wrapTokenKeyName('MesonLP:', tokenIndex), amount),
        Approve()
    )
    

# todo: this function (maybe) can merge with the above one
def deposit(
    amount: Int,
    tokenIndex: Int,
) -> Int:
    lp = Txn.sender()
    enumIndex = getEnumIndex(tokenIndex)
    
    return Seq(
        Assert(validateTokenReceived(Int(1), tokenIndex, amount, enumIndex)),
        App.localPut(
            lp, wrapTokenKeyName('MesonLP:', tokenIndex), 
            poolTokenBalance(lp, enumIndex) + amount
        ),
        Approve()
    )
    
    
# Step 0.3: lp withdraw
def withdraw(
    amount: Int,
    tokenIndex: Int,
) -> Int:
    lp = Txn.sender()
    enumIndex = getEnumIndex(tokenIndex)
    
    return Seq(
        Assert(poolTokenBalance(lp, enumIndex) >= amount),
        App.localPut(
            lp, wrapTokenKeyName('MesonLP:', tokenIndex), 
            poolTokenBalance(lp, enumIndex) - amount
        ),
        safeTransfer(tokenIndex, lp, amount, enumIndex),
        Approve()
    )
    

# Step 2.
def lock(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    initiator: Bytes,
) -> Int:
    
    outChain = itemFrom('outChain', encodedSwap)
    version = itemFrom('version', encodedSwap)
    amount = itemFrom('amount', encodedSwap) - itemFrom('feeForLP', encodedSwap)
    expireTs = itemFrom('expireTs', encodedSwap)
    until = Txn.first_valid_time() + cp.LOCK_TIME_PERIOD
    swapId = getSwapId(encodedSwap, initiator)
    lp = Txn.sender()
    enumIndexOut = itemFrom('outToken', encodedSwap)
    tokenIndexOut = getTokenIndex(enumIndexOut)
    lockedSwap = lockedSwapFrom(until, lp, enumIndexOut)
    
    conditions = And(
        outChain == cp.SHORT_COIN_TYPE,
        version == cp.MESON_PROTOCOL_VERSION,
        until < expireTs - Int(300),        # 5 minutes     # todo: check if it's 300 or 300,000
        checkRequestSignature(encodedSwap, r_s, v, initiator),
        poolTokenBalance(lp, enumIndexOut) > amount,
    )
    
    return Seq(
        Assert(conditions),
        App.localPut(
            lp, wrapTokenKeyName('MesonLP:', tokenIndexOut), 
            poolTokenBalance(lp, enumIndexOut) - amount
        ),
        Assert(App.box_create(swapId, Int(41))),
        App.box_put(swapId, lockedSwap),
        Approve()
    )
    


# -------------------------------------- For Test --------------------------------------
if __name__ == '__main__':
    
    def mesonpools_program_func():
        return Cond(
            [Txn.application_id() == Int(0), Approve()],
            [
                Txn.on_completion() == OnComplete.NoOp,
                Cond([
                    Txn.application_args[0] == Bytes("lock"),
                    lock(
                        Txn.application_args[1], 
                        Btoi(Txn.application_args[2]),
                        Btoi(Txn.application_args[3]),
                        Txn.application_args[4],
                    )
                ])
            ]
        )
    
    from test_run import TealApp
    ta = TealApp()
    ta.create_app(mesonpools_program_func, 'mesonpools.teal', [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 0x183301, 3])