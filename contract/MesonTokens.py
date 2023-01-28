from pyteal import *


# Directly using global index to map
def _addSupportToken(tokenIndex: Int, enumIndex: Int):
    # todo: onlyDeployer
    
    Assert(enumIndex != Int(0))
    Assert(tokenIndex != Int(0))
    Assert(App.globalGet(wrapTokenKeyName(enumIndex, 'EnumIndex:')) == Int(0))
    Assert(App.globalGet(wrapTokenKeyName(tokenIndex, 'TokenIndex:')) == Int(0))
    
    App.globalPut(wrapTokenKeyName(enumIndex, 'EnumIndex:'), tokenIndex)
    App.globalPut(wrapTokenKeyName(tokenIndex, 'TokenIndex:'), enumIndex)
    
    
def wrapTokenKeyName(enumIndex: Int, suffix: str) -> Bytes:
    '''
        Int(15) -> Bytes('enumIndex:000000000000000f')
    '''
    return Concat(Bytes(suffix), Itob(enumIndex))
