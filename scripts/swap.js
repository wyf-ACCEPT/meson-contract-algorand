const dotenv = require('dotenv')
const {
  makeApplicationCallTxnFromObject,
  makeAssetTransferTxnWithSuggestedParamsFromObject,
} = require('algosdk')
const { readFileSync } = require('fs')
const { AlgorandUtils } = require('./algorand_utils')
dotenv.config()

swap()

// Start a classic Meson-swap process.
async function swap() {
  const metadata = JSON.parse(readFileSync('./scripts/metadata.json'))
  const { usdc_index, usdt_index, meson_index, meson_address } = metadata

  const utils = new AlgorandUtils()
  const { alice, bob, carol, on_complete_param, initiator_buffer, initiator_address, listToUint8ArrayList, submit_transaction, submit_transaction_group, sp_func, build_encoded, get_swapID, get_expire_ts, sign_request, sign_release, show_boxes } = utils

  const amount_swap = parseInt((7 + Math.random() * 3) * 1_000_000)
  const encoded_hexstring = build_encoded(amount_swap, get_expire_ts(), '02', '01', false)
  const encoded_bytes = Buffer.from(encoded_hexstring, 'hex')
  console.log(`EncodedSwap: ${encoded_hexstring}`)


  console.log("\n\n================== 3.1 PostSwap & BondSwap ==================")

  let [r, s, v] = sign_request(encoded_hexstring)
  console.log("Complete request signing!")

  let postSwap_group = [
    makeApplicationCallTxnFromObject({
      from: carol.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['postSwap', encoded_bytes, r, s, v, initiator_buffer]),
      boxes: [{
        appIndex: meson_index,
        name: new Uint8Array(encoded_bytes),
      }],
    }),
    makeAssetTransferTxnWithSuggestedParamsFromObject({
      from: carol.addr,
      suggestedParams: await sp_func(),
      to: meson_address,
      amount: amount_swap,
      assetIndex: usdc_index,
    }),
  ]
  for (let pad_index = 0; pad_index < 7; pad_index++)
    postSwap_group.push(makeApplicationCallTxnFromObject({
      from: carol.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['padding', pad_index]),
    }))
  await submit_transaction_group(carol.sk, postSwap_group)
  console.log("Step 1.1. User(Carol) posted swap success!\n")

  await submit_transaction(bob.sk, makeApplicationCallTxnFromObject({
    from: bob.addr,
    suggestedParams: await sp_func(),
    appIndex: meson_index,
    onComplete: on_complete_param,
    appArgs: listToUint8ArrayList(['bondSwap', encoded_bytes]),
    boxes: [{
      appIndex: meson_index,
      name: new Uint8Array(encoded_bytes),
    }],
  }))
  console.log("Step 1.2. LP(Bob) Bonded swap success!\n")
  await show_boxes(meson_index, true)


  console.log("\n\n================== 3.2 Lock ==================")

  let lock_group = [
    makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['lock', encoded_bytes, r, s, v, initiator_buffer]),
      accounts: [carol.addr],
      boxes: [{
        appIndex: meson_index,
        name: new Uint8Array(get_swapID(encoded_hexstring, initiator_address)),
      }],
    }),
  ]
  for (let pad_index = 0; pad_index < 8; pad_index++)
    lock_group.push(makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['padding', pad_index]),
    }))
  await submit_transaction_group(bob.sk, lock_group)
  console.log("Step 2. LP(Bob) lock assets success!\n")
  await show_boxes(meson_index, false)


  console.log("\n\n================== 3.3 Release ==================")

  let [r2, s2, v2] = sign_release(encoded_hexstring, carol.addr)
  console.log("Complete release signing!")

  let release_group = [
    makeApplicationCallTxnFromObject({
      from: carol.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['release', encoded_bytes, r2, s2, v2, initiator_buffer]),
      foreignAssets: [usdt_index],
      boxes: [{
        appIndex: meson_index,
        name: new Uint8Array(get_swapID(encoded_hexstring, initiator_address)),
      }],
    }),
  ]
  for (let pad_index = 0; pad_index < 8; pad_index++)
    release_group.push(makeApplicationCallTxnFromObject({
      from: carol.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['padding', pad_index]),
    }))
  await submit_transaction_group(carol.sk, release_group)
  console.log("Step 3. User(Carol) release assets success!\n")
  await show_boxes(meson_index, false)


  console.log("\n\n================== 3.4 ExecuteSwap ==================")

  let executeSwap_group = [
    makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['executeSwap', encoded_bytes, r2, s2, v2, 1]),
      accounts: [carol.addr],
      foreignAssets: [usdc_index],
      boxes: [{
        appIndex: meson_index,
        name: new Uint8Array(encoded_bytes),
      }],
    }),
  ]
  for (let pad_index = 0; pad_index < 7; pad_index++)
    executeSwap_group.push(makeApplicationCallTxnFromObject({
      from: bob.addr,
      suggestedParams: await sp_func(),
      appIndex: meson_index,
      onComplete: on_complete_param,
      appArgs: listToUint8ArrayList(['padding', pad_index]),
    }))
  await submit_transaction_group(bob.sk, executeSwap_group)
  console.log("Step 4. LP(Bob) executeSwap success!\n")
  await show_boxes(meson_index, true)

}