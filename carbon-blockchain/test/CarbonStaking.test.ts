import { describe, it } from "node:test";
import assert from "node:assert";
import { network } from "hardhat";
import { getAddress, parseEther, toHex } from "viem";

describe("CarbonStaking & ZK-ML Protocol", async () => {
  const { viem, networkHelpers } = await network.create();

  // We define a fixture to reuse the same setup in every test.
  async function deployProtocolFixture() {
    // Get local testing accounts (Enterprise and Validator)
    const [owner, enterprise, validator] = await viem.getWalletClients();
    const publicClient = await viem.getPublicClient();

    // 1. Deploy the Mock Verifier
    const verifier = await viem.deployContract("Verifier");

    // 2. Deploy the Carbon Staking Contract, passing the Verifier's address
    const staking = await viem.deployContract("CarbonStaking", [
      verifier.address,
    ]);

    return { verifier, staking, owner, enterprise, validator, publicClient };
  }

  describe("Deployment & Staking", () => {
    it("Should allow an enterprise to stake 1 ETH and set score to 100", async () => {
      const { staking, enterprise } = await networkHelpers.loadFixture(deployProtocolFixture);

      // Enterprise stakes 1 ETH
      const stakeAmount = parseEther("1");
      await staking.write.registerAndStake({
        value: stakeAmount,
        account: enterprise.account,
      });

      // Fetch the enterprise's state from the blockchain
      const enterpriseData = await staking.read.enterprises([
        getAddress(enterprise.account.address),
      ]);

      // enterpriseData returns a tuple: [stakedAmount, reliabilityScore, totalCreditsMinted, isActive]
      assert.strictEqual(enterpriseData[0], stakeAmount);
      assert.strictEqual(enterpriseData[1], 100n); // Reliability starts at 100
      assert.strictEqual(enterpriseData[3], true);     // isActive
    });
  });

  describe("ML Validation & Slashing", () => {
    it("Should REWARD the enterprise for a VALID machine learning proof", async () => {
      const { staking, enterprise, validator } = await networkHelpers.loadFixture(deployProtocolFixture);

      // Setup: Enterprise stakes first
      await staking.write.registerAndStake({
        value: parseEther("1"),
        account: enterprise.account,
      });

      // The Validator Oracle submits a VALID proof (0x01)
      const validProof = toHex(new Uint8Array([1]));
      const pubInputs: bigint[] = [];
      const expectedCO2 = 500n; // Synthesized CO2 output from ML

      await staking.write.submitValidation(
        [getAddress(enterprise.account.address), validProof, pubInputs, expectedCO2],
        { account: validator.account }
      );

      // Verify Rewards
      const data = await staking.read.enterprises([getAddress(enterprise.account.address)]);
      assert.strictEqual(data[1], 101n); // Score increased by 1
      assert.strictEqual(data[2], expectedCO2); // Credits minted
    });

    it("Should SLASH the enterprise for a FRAUDULENT proof (The Analog Hole)", async () => {
      const { staking, enterprise, validator } = await networkHelpers.loadFixture(deployProtocolFixture);

      // Setup: Enterprise stakes first
      await staking.write.registerAndStake({
        value: parseEther("1"),
        account: enterprise.account,
      });

      // The Validator Oracle runs the ML model, catches physical tampering, and submits a FAILED proof (0x00)
      const fraudProof = toHex(new Uint8Array([0]));
      const pubInputs: bigint[] = [];
      const expectedCO2 = 0n;

      await staking.write.submitValidation(
        [getAddress(enterprise.account.address), fraudProof, pubInputs, expectedCO2],
        { account: validator.account }
      );

      // Verify Slashing
      const data = await staking.read.enterprises([getAddress(enterprise.account.address)]);
      assert.strictEqual(data[0], parseEther("0.8")); // 1.0 ETH minus 0.2 ETH penalty
      assert.strictEqual(data[1], 90n); // Score dropped by 10 points
    });
  });
});
