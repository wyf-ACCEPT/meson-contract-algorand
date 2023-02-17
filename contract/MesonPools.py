from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initPools() -> Int:
    return Seq(
        Approve()
    )


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
    lockAmount = itemFrom('amount', encodedSwap) - itemFrom('feeForLP', encodedSwap)
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
        poolTokenBalance(lp, enumIndexOut) > lockAmount,
    )
    
    return Seq(
        Assert(conditions),
        App.localPut(
            lp, wrapTokenKeyName('MesonLP:', tokenIndexOut), 
            poolTokenBalance(lp, enumIndexOut) - lockAmount
        ),
        Assert(App.box_create(swapId, Int(41))),
        App.box_put(swapId, lockedSwap),
        Approve()
    )



# Step 3. 
def release(
    encodedSwap: Bytes,
    r_s: Int,
    v: Int,
    initiator: Bytes,
    recipient: Bytes,
) -> Int:
            # todo: Txn.sender() == <tx.origin>?
            # todo: _onlyPremiumManager
    feeWaived = extraItemFrom('_feeWaived', encodedSwap)
    expireTs = itemFrom('expireTs', encodedSwap)
    swapId = getSwapId(encodedSwap, initiator)
    currentAddr = Global.current_application_address()
    enumIndexOut = itemFrom('outToken', encodedSwap)
    tokenIndexOut = getTokenIndex(enumIndexOut)
    serviceFee = extraItemFrom('_serviceFee', encodedSwap)
    releaseAmount = ScratchVar(TealType.uint64)
    
    conditions = And(
        Seq(
            lockedSwap_get := App.box_get(swapId),
            Assert(lockedSwap_get.hasValue()),
            lockedSwap_get.value() != cp.LOCKED_SWAP_FINISH
        ),
        recipient != cp.ZERO_ADDRESS,
        expireTs > Txn.first_valid_time(),
        checkReleaseSignature(encodedSwap, recipient, r_s, v, initiator),
    )
    
    return Seq(
        Assert(conditions),
        App.box_put(swapId, cp.LOCKED_SWAP_FINISH),
        releaseAmount.store(itemFrom('amount', encodedSwap) - itemFrom('feeForLP', encodedSwap)),
        If(
            Not(feeWaived),
            Seq(
                releaseAmount.store(releaseAmount.load() - serviceFee),
                App.localPut(
                    currentAddr, 
                    wrapTokenKeyName('MesonLP:', tokenIndexOut), 
                    poolTokenBalance(currentAddr, enumIndexOut) + serviceFee
                ),
            )
        ),          # todo: transferToContract
        safeTransfer(tokenIndexOut, recipient, releaseAmount.load(), enumIndexOut),    
        Approve()
    )



# ------------------------------------ Main Program ------------------------------------
def mesonPoolsMainFunc():
    return Cond(
        [
            Or(
                Txn.application_id() == Int(0),
                Txn.on_completion() == OnComplete.OptIn
            ), 
            Approve()
        ], [
            Or(
                Txn.on_completion() == OnComplete.CloseOut,
                Txn.on_completion() == OnComplete.UpdateApplication,
                Txn.on_completion() == OnComplete.DeleteApplication,        # todo
            ),
            Reject(),
        ], [
            Txn.on_completion() == OnComplete.NoOp,
            Cond([
                Txn.application_args[0] == Bytes("addSupportToken"),
                addSupportToken(
                    Btoi(Txn.application_args[1]),
                    Btoi(Txn.application_args[2]),
                )
            ], [
                Txn.application_args[0] == Bytes("lock"),
                lock(
                    Txn.application_args[1], 
                    Btoi(Txn.application_args[2]),
                    Btoi(Txn.application_args[3]),
                    Txn.application_args[4],
                )
            ], [
                Txn.application_args[0] == Bytes("release"),
                release(
                    Txn.application_args[1], 
                    Btoi(Txn.application_args[2]),
                    Btoi(Txn.application_args[3]),
                    Txn.application_args[4],
                    Txn.application_args[5],
                )
            ])
        ]
    )



# -------------------------------------- For Test --------------------------------------
if __name__ == '__main__':
    from test_run import TealApp
    ta = TealApp()
    open('./compiled_teal/%s' % 'mesonpools.teal', 'w').write(
        compileTeal(mesonPoolsMainFunc(), Mode.Application, version=8)
    )
    # ta.create_app(mesonPoolsMainFunc, 'mesonpools.teal', [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 0x183301, 3])