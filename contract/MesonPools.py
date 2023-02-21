from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *
from MesonTokens import *


def initMesonPools() -> Int:
    return Approve()


def _updateBalanceOfPool(
    Bytes: lp,
    assetId: Int,
    balance: Int,
) -> Int:
    return App.localPut(lp, _storageKey("MesonLP:", assetId), balance)

def depositAndRegister(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = _getTokenIndex(assetId)

    conditions = And(
        _validateTokenReceived(Int(1), assetId, amount, tokenIndex),
        poolTokenBalance(lp, tokenIndex) == Int(0),
    )

    return Seq(
        Assert(conditions),
        _updateBalanceOfPool(lp, assetId, amount),
        Approve(),
    )


# todo: this function (maybe) can merge with the above one
def deposit(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = _getTokenIndex(assetId)

    return Seq(
        Assert(_validateTokenReceived(Int(1), assetId, amount, tokenIndex)),
        _updateBalanceOfPool(lp, assetId, poolTokenBalance(lp, tokenIndex) + amount),
        Approve(),
    )


# Step 0.3: lp withdraw
def withdraw(
    amount: Int,
    assetId: Int,
) -> Int:
    lp = Txn.sender()
    tokenIndex = _getTokenIndex(assetId)

    return Seq(
        Assert(poolTokenBalance(lp, tokenIndex) >= amount),
        _updateBalanceOfPool(lp, assetId, poolTokenBalance(lp, tokenIndex) - amount),
        _safeTransfer(assetId, lp, amount, tokenIndex),
        Approve(),
    )


# Step 2.
def lock(
    encodedSwap: Bytes,
    r: Int,
    sv: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
    recipient: Bytes,
) -> Int:
    outChain = _decodeSwap(encodedSwap, "outChain")
    version = _decodeSwap(encodedSwap, "version")
    lockAmount = _decodeSwap(encodedSwap, "amount") - _decodeSwap(encodedSwap, "feeForLP")
    expireTs = _decodeSwap(encodedSwap, "expireTs")
    until = Txn.first_valid_time() + cp.LOCK_TIME_PERIOD
    swapId = _getSwapId(encodedSwap, initiator)
    lp = Txn.sender()
    tokenIndexOut = _decodeSwap(encodedSwap, "outToken")
    assetIdOut = _getAssetId(tokenIndexOut)
    lockedSwap = _lockedSwapFrom(lp, until, recipient)

    conditions = And(
        outChain == cp.SHORT_COIN_TYPE,
        version == cp.MESON_PROTOCOL_VERSION,
        until < expireTs - Int(300),  # 5 minutes     # todo: check if it's 300 or 300,000
        _checkRequestSignature(encodedSwap, r, sv, initiator),
        poolTokenBalance(lp, tokenIndexOut) > lockAmount,
    )

    return Seq(
        Assert(conditions),
        _updateBalanceOfPool(lp, assetIdOut, poolTokenBalance(lp, tokenIndexOut) - lockAmount),
        Assert(App.box_create(swapId, Int(38))),
        App.box_put(swapId, lockedSwap),
        Approve(),
    )


# Step 3.
def release(
    encodedSwap: Bytes,
    r: Int,
    sv: Int,
    initiator: Bytes,  # This variable is bring from Txn.accounts
    recipient: Bytes,  # This variable is bring from Txn.accounts
) -> Int:
    # todo: Txn.sender() == <tx.origin>?
    # todo: _onlyPremiumManager
    feeWaived = _extraItemFrom("_feeWaived", encodedSwap)
    expireTs = _decodeSwap(encodedSwap, "expireTs")
    swapId = _getSwapId(encodedSwap, initiator)
    tokenIndexOut = _decodeSwap(encodedSwap, "outToken")
    assetIdOut = _getAssetId(tokenIndexOut)
    serviceFee = _extraItemFrom("_serviceFee", encodedSwap)
    releaseAmount = ScratchVar(TealType.uint64)

    conditions = And(
        Seq(
            lockedSwap_get := App.box_get(swapId),
            Assert(lockedSwap_get.hasValue()),
            lockedSwap_get.value() != cp.LOCKED_SWAP_FINISH,
        ),
        recipient != cp.ZERO_ADDRESS,
        expireTs > Txn.first_valid_time(),
        _checkReleaseSignature(encodedSwap, recipient, r, sv, initiator),
    )

    return Seq(
        Assert(conditions),
        App.box_put(swapId, cp.LOCKED_SWAP_FINISH),
        releaseAmount.store(
            _decodeSwap(encodedSwap, "amount") - _decodeSwap(encodedSwap, "feeForLP")
        ),
        If(
            Not(feeWaived),
            Seq(
                releaseAmount.store(releaseAmount.load() - serviceFee),
                App.globalPut(
                    _storageKey("ProtocolFee:", assetIdOut),
                    App.globalGet(_storageKey("ProtocolFee:", assetIdOut))
                    + serviceFee,
                ),
            ),
        ),  # todo: transferToContract
        _safeTransfer(assetIdOut, recipient, releaseAmount.load(), tokenIndexOut),
        Approve(),
    )

