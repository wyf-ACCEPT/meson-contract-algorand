const dotenv = require('dotenv')
const {
  makeAssetTransferTxnWithSuggestedParamsFromObject,
  makeApplicationOptInTxn,
  makeApplicationCallTxnFromObject,
} = require('algosdk')
const { readFileSync } = require('fs')
const { AlgorandUtils } = require('./algorand_utils')
dotenv.config()

mint()

// Actually this is a `transfer from admin to user` function, not a `mint to user` function.
// After receiving the assets, the LP will deposit the USDC/USDT into Meson App.
async function mint() {
  const metadata = JSON.parse(readFileSync('./scripts/metadata.json'))
  const { usdc_index, usdt_index, meson_index, meson_address } = metadata

  const utils = new AlgorandUtils()
  const { alice, bob, carol, on_complete_param, listToUint8ArrayList, submit_transaction, submit_transaction_group, sp_func } = utils

  const mint_num = 400_000 * 1_000_000
  const lp_deposit_amount = 250 * 1_000_000


  console.log("================== 2.1 LP and User receive assets ==================")
  await submit_transaction_group(alice.sk, [
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: alice.addr, suggestedParams: await sp_func(), amount: mint_num,
      to: bob.addr, assetIndex: usdc_index,
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: alice.addr, suggestedParams: await sp_func(), amount: mint_num,
      to: carol.addr, assetIndex: usdc_index,
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: alice.addr, suggestedParams: await sp_func(), amount: mint_num,
      to: bob.addr, assetIndex: usdt_index,
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: alice.addr, suggestedParams: await sp_func(), amount: mint_num,
      to: carol.addr, assetIndex: usdt_index,
    }),
  ])
  console.log(`LP(Bob) and User(Carol) both received ${mint_num / 1e6} USDC & USDT!\n`)


  console.log("\n================== 2.2 LP Opt in App ==================")
  await submit_transaction(bob.sk, makeApplicationOptInTxn(
    bob.addr, await sp_func(), meson_index,
  ))
  console.log("LP(Bob) opt in Meson App success!\n")


  console.log("\n================== 2.3 LP deposit to App ==================")
  await submit_transaction_group(bob.sk, [
    makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['deposit', lp_deposit_amount]),
      foreignAssets: [usdc_index]
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      to: meson_address,
      amount: lp_deposit_amount,
      assetIndex: usdc_index,
    })
  ],)
  console.log(`LP(Bob) deposit ${lp_deposit_amount / 1e6} mUSDC into Meson App!\n`)

  await submit_transaction_group(bob.sk, [
    makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['deposit', lp_deposit_amount]),
      foreignAssets: [usdt_index]
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      to: meson_address,
      amount: lp_deposit_amount,
      assetIndex: usdt_index,
    })
  ],)
  console.log(`LP(Bob) deposit ${lp_deposit_amount / 1e6} mUSDT into Meson App!`)
  console.log("[TODO] Cannot use indexer to see local state correctly!\n")
}