const { Algodv2 } = require("algosdk");

const network_main = {
  "id": "algo",
  "name": "Algorand",
  "alias": "ALGO",
  "chainId": "0x11b",
  "slip44": "0x8000011b",
  "shortSlip44": "0x011b",
  "extensions": [],
  "addressFormat": "",
  "url": "https://mainnet-api.algonode.network",
  "explorer": "https://algoexplorer.io/",
  "mesonAddress": "",
  "tokens": [],
}

const network_test = {
  "id": "algo-testnet",
  "name": "Algorand Testnet",
  "alias": "ALGO",
  "chainId": "0x11b",
  "slip44": "0x8000011b",
  "shortSlip44": "0x011b",
  "extensions": [],
  // "addressFormat": "",
  "url": "https://testnet-api.algonode.network",
  "explorer": "https://testnet.algoexplorer.io/",
  "mesonAddress": "",
  "tokens": []
}

class MesonPresets {
  constructor(networks = [network_main, network_test]) {
    this.networks = networks
  }

  useTestnet(testnet) {
    if (testnet) this.use_network = this.networks[1]
    else this.use_network = this.networks[0]
  }

  getNetwork(id) {
    if (id == 'algorand-testnet') return this.networks[1]
    else if (id == 'algorand-mainnet') return this.networks[0]
    else throw new Error('Invalid network ID. Only `algorand-testnet` and `algorand-mainnet` is available!')
  }

  createNetworkClient(id, urls = [], opts) {
    return new Algodv2(
      'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
      this.getNetwork(id).url
    )
  }
}

module.exports = new MesonPresets();
