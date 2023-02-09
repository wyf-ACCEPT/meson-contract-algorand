from typing import Union

from pyteal import *

from MesonConfig import ConfigParams as cp
from MesonHelpers import *


def postSwap(
    encodedSwap: Bytes,
    r: Bytes,
    s: Bytes,
    v: Int,
    postingValue: Bytes,
) -> Int:
    amount = itemFrom('amount', encodedSwap)
    delta = itemFrom('expireTs', encodedSwap) - Txn.first_valid_time()
    
    conditions = And(
        amount < cp.MAX_SWAP_AMOUNT,
        delta > cp.MIN_BOND_TIME_PERIOD,
        delta < cp.MAX_BOND_TIME_PERIOD,
    )
    
    return Seq(
        Assert(conditions),
        Assert()
        
    )
