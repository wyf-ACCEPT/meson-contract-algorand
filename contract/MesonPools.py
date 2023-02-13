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
    
