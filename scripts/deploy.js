const hre = require("hardhat");

async function main() {

  // Deploy OrgRegistry
  const OrgRegistry = await hre.ethers.getContractFactory("OrgRegistry");
  const orgRegistry = await OrgRegistry.deploy();
  await orgRegistry.waitForDeployment();
  const orgAddress = await orgRegistry.getAddress();
  console.log("OrgRegistry deployed to:", orgAddress);

  // Deploy CTIRegistry (needs OrgRegistry address)
  const CTIRegistry = await hre.ethers.getContractFactory("CTIRegistry");
  const ctiRegistry = await CTIRegistry.deploy(orgAddress);
  await ctiRegistry.waitForDeployment();
  const ctiAddress = await ctiRegistry.getAddress();
  console.log("CTIRegistry deployed to:", ctiAddress);

  // Deploy Reputation (needs OrgRegistry + CTIRegistry addresses)
  const Reputation = await hre.ethers.getContractFactory("Reputation");
  const reputation = await Reputation.deploy(orgAddress, ctiAddress);
  await reputation.waitForDeployment();
  const reputationAddress = await reputation.getAddress();
  console.log("Reputation deployed to:", reputationAddress);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
