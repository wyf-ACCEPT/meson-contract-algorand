const dotenv = require('dotenv')
const {

} = require('algosdk')
const { readFileSync } = require('fs')
const { AlgorandUtils } = require('./algorand_utils')
dotenv.config()

// Some view functions that may be used.
main()

async function main() {

  const metadata = JSON.parse(readFileSync('./scripts/metadata.json'))
  const { usdc_index, usdt_index, meson_index, meson_address } = metadata

  const utils = new AlgorandUtils()
  const { alice, bob, carol, encoder, on_complete_param, initiator_buffer, initiator_address, client, indexer, listToUint8ArrayList, submit_transaction, submit_transaction_group, sp_func, build_encoded, get_swapID, get_expire_ts, sign_request, sign_release, show_boxes } = utils



  console.log("\ngetSupportedTokens: ");
  (await getSupportedTokens(client, meson_index))
    .map(line => console.log(line))

  // console.log("\nownerOfPoolList (Overall): ")
  // console.log(await ownerOfPoolList(provider, metadata))

  // console.log("\nownerOfPool (Specified): ")
  // console.log(await ownerOfPool(provider, metadata, 1))

  // console.log("\nownerOfPool (Specified, expected failed): ")
  // console.log(await ownerOfPool(provider, metadata, 2))

  // console.log("\npoolOfAuthorizedAddrList (Overall): ")
  // console.log(await poolOfAuthorizedAddrList(provider, metadata))

  // console.log("\npoolOfAuthorizedAddr (Specified): ")
  // console.log(await poolOfAuthorizedAddr(
  //   provider, metadata, '0x612ab2d8d1d9f250b458fb5e41b4c7989d5997cb67f8263b65a79dbac541d631'
  // ))

  // console.log("\npoolOfAuthorizedAddr (Specified, expected failed): ")
  // console.log(await poolOfAuthorizedAddr(
  //   provider, metadata, '0x612ab2d8d1d9f250b458fb5e41b4c7989d5997cb67f8263b65a79dbac541d632'
  // ))

  // console.log("\ngetPostedSwap (Specified): ")
  // console.log(await getPostedSwap(
  //   provider, metadata, '0x00004c4b408000000000008308cf8700000000000064475180031001031001ff'
  // ))

  // console.log("\ngetPostedSwap (Specified, expected failed): ")
  // console.log(await getPostedSwap(
  //   provider, metadata, '0x00004c4b408000000000008308cf870000000000006447518003100103100200'
  // ))

  // console.log("\npoolTokenBalance (Specified):")
  // console.log(await poolTokenBalance(provider, metadata, 155))

  // console.log("\npoolTokenBalance (Specified, expected failed):")
  // console.log(await poolTokenBalance(provider, metadata, 1))



  // await getSupportedTokens(indexer, meson_index)

  // var r = await indexer.searchForApplicationBoxes(meson_index)
  // var r = await indexer.lookupApplications(meson_index).do()
  // console.log(r)

  // // local states
  // var r = await client.accountApplicationInformation(bob.addr, meson_index).do()

  // // boxes
  // var r = await client.getApplicationBoxes(meson_index).do()

  // global states
  var r = await client.getApplicationByID(meson_index).do()

}


async function getSupportedTokens(provider, meson_index) {
  const global_states_raw = (await provider.getApplicationByID(meson_index).do()).params["global-state"]

  const supported_coins_list = await Promise.all(
    global_states_raw
      .filter(state => Buffer.from(state.key, 'base64').toString().includes('AssetId'))
      .map(async state => {
        const assetId = parseInt(Buffer.from(state.key, 'base64').toString('hex').slice(16), 16)
        const tokenIndex = state.value.uint
        const assetInfo = (await provider.getAssetByID(assetId).do()).params
        const [name, symbol] = [assetInfo['name'], assetInfo['unit-name']]
        return { assetId, tokenIndex, name, symbol };
      })
  )

  return supported_coins_list
}





// async function ownerOfPoolList(provider, metadata) {
//   const pool_owners_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.pool_owners.fields.id.id
//   })).data

//   const pool_owners_list = await Promise.all(pool_owners_raw.map(async pool_raw => ({
//     poolId: pool_raw.name.value,
//     address: (await provider.getObject(
//       { id: pool_raw.objectId, options: { showContent: true } }
//     )).data.content.fields.value
//   })))

//   return pool_owners_list
// }


// async function ownerOfPool(provider, metadata, poolId) {
//   const pool_owners_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.pool_owners.fields.id.id
//   })).data

//   try {
//     const pool = pool_owners_raw.filter(pool => pool.name.value == poolId)[0]
//     const pool_address = (await provider.getObject(
//       { id: pool.objectId, options: { showContent: true } }
//     )).data.content.fields.value
//     return pool_address
//   }
//   catch (err) {
//     console.log(`Wrong poolId ${poolId}!`)
//   }
// }


// async function poolOfAuthorizedAddrList(provider, metadata) {
//   const auth_addr_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.pool_of_authorized_addr.fields.id.id
//   })).data

//   const auth_addr_list = await Promise.all(auth_addr_raw.map(async auth => ({
//     address: auth.name.value,
//     poolId: (await provider.getObject(
//       { id: auth.objectId, options: { showContent: true } }
//     )).data.content.fields.value
//   })))

//   return auth_addr_list
// }


// async function poolOfAuthorizedAddr(provider, metadata, address) {
//   const auth_addr_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.pool_of_authorized_addr.fields.id.id
//   })).data

//   try {
//     const pool = auth_addr_raw.filter(auth => auth.name.value == address)[0]
//     const poolId = (await provider.getObject(
//       { id: pool.objectId, options: { showContent: true } }
//     )).data.content.fields.value
//     return poolId
//   }
//   catch (err) {
//     console.log(`Unauthrized address ${address}!`)
//   }
// }


// async function getPostedSwap(provider, metadata, encoded) {
//   const posted_swaps_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.posted_swaps.fields.id.id
//   })).data

//   try {
//     const posted_key = posted_swaps_raw.filter(
//       posted_raw => arrayToHex(posted_raw.name.value.slice(1)) == encoded
//     )[0]
//     const posted_value = (await provider.getObject(
//       { id: posted_key.objectId, options: { showContent: true } }
//     )).data.content.fields.value.fields
//     return posted_value
//   }
//   catch (err) {
//     console.log(`Encodedswap value ${encoded} doesn't exists!`)
//   }
// }


// async function getLockedSwap(provider, metadata, swapId) {
//   const locked_swaps_raw = (await provider.getDynamicFields({
//     parentId: metadata.storeG_content.locked_swaps.fields.id.id
//   })).data

//   try {
//     const locked_key = locked_swaps_raw.filter(
//       locked_raw => arrayToHex(locked_raw.name.value.slice(1)) == swapId
//     )[0]
//     const locked_value = (await provider.getObject(
//       { id: locked_key.objectId, options: { showContent: true } }
//     )).data.content.fields.value.fields
//     return locked_value
//   }
//   catch (err) {
//     console.log(`SwapId ${swapId} value not exists!`)
//   }
// }     // Haven't test!


// async function poolTokenBalance(provider, metadata, poolId) {
//   let coin_balances = {}

//   for (var name in metadata.storeC) {
//     const coin_pool_object = (await provider.getObject({
//       id: metadata.storeC[name], options: { showContent: true }
//     })).data.content.fields.in_pool_coins.fields.id.id

//     const coin_pool_raw = (await provider.getDynamicFields({
//       parentId: coin_pool_object
//     })).data

//     try {
//       const coin_pool = coin_pool_raw.filter(item => item.name.value == poolId)[0]
//       const coin_balance = (await provider.getObject(
//         { id: coin_pool.objectId, options: { showContent: true } }
//       )).data.content.fields.value.fields.balance
//       coin_balances[name] = coin_balance
//     }
//     catch (err) {
//       console.log(`PoolId ${poolId} not exists in ${name} pool!`)
//     }
//   }
//   return coin_balances
// }