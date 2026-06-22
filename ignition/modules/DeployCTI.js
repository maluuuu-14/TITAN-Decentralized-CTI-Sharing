const { buildModule } = require("@nomicfoundation/hardhat-ignition/modules");

module.exports = buildModule("CTIModule", (m) => {
  const orgRegistry = m.contract("OrgRegistry");
  const ctiRegistry = m.contract("CTIRegistry", [orgRegistry]);
  const reputation = m.contract("Reputation", [orgRegistry, ctiRegistry]);

  return { orgRegistry, ctiRegistry, reputation };
});