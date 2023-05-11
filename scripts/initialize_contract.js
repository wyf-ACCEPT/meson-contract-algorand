const dotenv = require('dotenv')
const { 
  makeApplicationCreateTxn, 
  makeApplicationCallTxnFromObject,
  makePaymentTxnWithSuggestedParams,
  getApplicationAddress,
} = require('algosdk')
const { writeFileSync, readFileSync } = require('fs')
const { AlgorandUtils } = require('./algorand_utils')
dotenv.config()

initialize()

// Deploy the contract and opt in USDC & USDT. Save the appId and appAddress to `metadata.json`.
async function initialize() {
  const metadata = JSON.parse(readFileSync('./scripts/metadata.json'))
  const { usdc_index, usdt_index } = metadata

  const utils = new AlgorandUtils()
  const { alice, on_complete_param, listToUint8ArrayList, submit_transaction, sp_func } = utils
  await utils.show_account_info()

  const transfer_to_app_amount = 400_000

  
  console.log("================== 1.1 Create Meson App ==================")
  let blank_program = await utils.compile_program('#pragma version 8\nint 1\nreturn')
  let meson_program = await utils.compile_program(utils.meson_contract_code)

  let create_app_tx = await submit_transaction(alice.sk, makeApplicationCreateTxn(
    alice.addr, await sp_func(), on_complete_param, meson_program, blank_program,
    6, 0, 12, 0, undefined, undefined, undefined, undefined, undefined, undefined,
    undefined, 1, undefined
  ))
  let meson_index = create_app_tx['application-index']
  let meson_address = getApplicationAddress(meson_index)
  console.log(`Create Meson Contract success! App id: ${meson_index}, App Address: ${meson_address}\n`)


  console.log("\n================== 1.2 Transfer to Meson ==================")
  await submit_transaction(alice.sk, makePaymentTxnWithSuggestedParams(
    alice.addr, meson_address, transfer_to_app_amount, undefined, undefined, await sp_func()
  ))
  console.log("Transfer $ALGO to Meson app success!")
  console.log(`App ${meson_index} balance: ${(await utils.client.accountInformation(meson_address).do()).amount / 1e6} ALGO.\n`)


  console.log("\n================== 1.3 Add USDC and USDT ==================")
  await submit_transaction(alice.sk, makeApplicationCallTxnFromObject({
    from: alice.addr,
    suggestedParams: await sp_func(),
    appIndex: meson_index,
    onComplete: on_complete_param,
    appArgs: listToUint8ArrayList(['addSupportToken', 1]),
    foreignAssets: [usdc_index],
  }))
  console.log("Meson App Optin USDC success!\n")
  await submit_transaction(alice.sk, makeApplicationCallTxnFromObject({
    from: alice.addr,
    suggestedParams: await sp_func(),
    appIndex: meson_index,
    onComplete: on_complete_param,
    appArgs: listToUint8ArrayList(['addSupportToken', 2]),
    foreignAssets: [usdt_index],
  }))
  console.log("Meson App Optin USDT success!\n")


  console.log("\n================== 1.4 Saved to metadata.json ==================")
  writeFileSync('./scripts/metadata.json', JSON.stringify(
    { meson_index, meson_address, ...metadata })
  )

}