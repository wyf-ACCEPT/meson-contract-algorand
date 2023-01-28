from pyteal import *
from MesonConfig import ConfigParams as cp




# ---------------------------------- encodedSwap processing ----------------------------------

# In pyteal, the type of `encodedSwap` should be `Bytes`, because type `Int` cannot be the key of Box variable.
# `encodedSwap`(Bytes: length=32): `version:uint8|amount:uint40|salt:uint80|fee:uint40|expireTs:uint40|outChain:uint16|outToken:uint8|inChain:uint16|inToken:uint8`

# ============ example ============
# origin format: [bytes32]
# \x01\x00\x01\xe8H\x00\xc0\x00\x00\x00\x00\x00\xe7U& \x00\x00\x00\x00\x00\x00c\xd5\x00B#)\x02\x02\xca
# hex format [uint256, hex64]:
# (0x)010001e84800c00000000000e755262000000000000063d5004223290202ca22
# split values: 0x|01|0001e84800|c00000000000e7552620|0000000000|0063d50042|2329|02|02ca|22
# split variables: 0x|version|amount|salt|fee|expireTs|outChain|outToken|inChain|inToken
# index(start-end): 0x | 0:1 | 1:6 | 6:16 | 16:21 | 21:26 | 26:28 | 28:29 | 29:31 | 31:32
# index(start-length): 0x | 0,1 | 1,5 | 6,10 | 16,5 | 21,5 | 26,2 | 28,1 | 29,2 | 31,1

def _versionFrom(encodedSwap: Bytes) -> Int:
    return Btoi(Substring(encodedSwap, Int(0), Int(1)))
