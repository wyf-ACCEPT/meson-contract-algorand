from pyteal import *


def optInToken(assetId: Int):
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                # TxnField.sender: Global.current_application_address(),
                # TxnField.asset_sender: Global.current_application_address(),
                TxnField.type_enum: TxnType.AssetTransfer,
                TxnField.xfer_asset: assetId,
                TxnField.asset_receiver: Global.current_application_address(),
                TxnField.asset_amount: Int(0),
            }
        ),
        InnerTxnBuilder.Submit(),
    )


def optInApp(appIndex: Int):
    return Seq(
        InnerTxnBuilder.Begin(),
        InnerTxnBuilder.SetFields(
            {
                TxnField.sender: Global.current_application_address(),
                TxnField.type_enum: TxnType.ApplicationCall,
                TxnField.application_id: appIndex,
                TxnField.on_completion: OnComplete.OptIn,
            }
        ),
        InnerTxnBuilder.Submit(),
    )


# Directly using global index to map:
def addSupportToken(assetId: Int, tokenIndex: Int) -> Int:
    # todo: onlyDeployer
    # todo: Optin

    #   Bytes('AssetId:17207135') -> Int(1)
    #   Bytes('TokenIndex:1') -> Int(17207135)
    return Seq(
        Assert(tokenIndex < Int(256)),
        Assert(tokenIndex != Int(0)),
        Assert(assetId != Int(0)),
        Assert(App.globalGet(wrapTokenKeyName("TokenIndex:", tokenIndex)) == Int(0)),
        Assert(App.globalGet(wrapTokenKeyName("AssetId:", assetId)) == Int(0)),
        App.globalPut(wrapTokenKeyName("TokenIndex:", tokenIndex), assetId),
        App.globalPut(wrapTokenKeyName("AssetId:", assetId), tokenIndex),
        # App.localPut(
        #     Global.current_application_address(),
        #     wrapTokenKeyName('MesonLP:', assetId),
        #     Int(0)
        # ), # use globalPut because an app cannot has local variables of itself (?)
        App.globalPut(wrapTokenKeyName("ProtocolFee:", assetId), Int(0)),
        optInToken(assetId),
        Approve(),
    )


def wrapTokenKeyName(suffix: str, index: Int) -> Bytes:
    return Concat(Bytes(suffix), Itob(index))


def getTokenIndex(assetId: Int) -> Int:
    return App.globalGet(wrapTokenKeyName("AssetId:", assetId))


def getAssetId(tokenIndex: Int) -> Int:
    return App.globalGet(wrapTokenKeyName("TokenIndex:", tokenIndex))


def poolTokenBalance(
    lp: Bytes,
    tokenIndex: Int,
) -> Int:
    assetId = getAssetId(tokenIndex)
    return App.localGet(lp, wrapTokenKeyName("MesonLP:", assetId))


# getSupportedTokens: View explorer directly to get supported token list!
def mesontoken_program_func():
    return Cond(
        [Txn.application_id() == Int(0), Approve()],
        [
            Txn.on_completion() == OnComplete.NoOp,
            Cond(
                [
                    Txn.application_args[0] == Bytes("addSupportToken"),
                    addSupportToken(Txn.assets[0], Btoi(Txn.application_args[1])),
                ]
            ),
        ],
    )


# -------------------------------------- For Test --------------------------------------
if __name__ == "__main__":

    from test_run import TealApp

    ta = TealApp()
    ta.create_app(mesontoken_program_func, "mesontokens.teal", [5, 5, 0, 0])
    # ta.call_app(['addSupportToken', 3], foreign_assets=[159625952])
