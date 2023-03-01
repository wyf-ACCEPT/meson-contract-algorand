const { Wallet, SigningKey, utils } = require('ethers')

main = async () => {
    const pk = '4719806c5b87c68e046b7b958d4416f66ff752ce60a36d28c0b9c5f29cbc9ab0'
    const wallet = new Wallet(pk)
    const digest_hex = 'bd045242342bc4e3948a5029209b0e90e29e5a55dffff09113aa65b8ea997031'
    // const digest_hex = '7b521e60f64ab56ff03ddfb26df49be54b20672b7acfffc1adeb256b554ccb258626c2a6698ce7518c71a8e6c3c4c8739ac5a799c97997198b73d4cf694be601'
    const digest_bytes = Buffer.from(digest_hex, 'hex')
    console.log(digest_bytes)
    console.log(await wallet.signMessage(digest_bytes))
    console.log(wallet.signingKey.sign(digest_bytes))
}

main()