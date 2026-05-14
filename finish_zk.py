import ezkl
import os
import asyncio
import inspect
from pathlib import Path

async def safe_ezkl(func, *args, **kwargs):
    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result

async def finalize():
    # 1. Force STRICT Absolute Paths to prevent Windows/Rust pathing desync
    cwd = os.path.abspath(os.getcwd())
    artifact_dir = Path(cwd) / "ezkl_artifacts"
    
    circuit = str(artifact_dir / "circuit.json")
    vk = str(artifact_dir / "vk.key")
    pk = str(artifact_dir / "pk.key")
    srs = str(artifact_dir / "kzg.srs")
    settings = str(artifact_dir / "settings.json")
    sol = str(artifact_dir / "Verifier.sol")
    abi = str(artifact_dir / "Verifier.abi")

    print(f"Working Directory: {cwd}")
    print("Checking critical files...")
    if not os.path.exists(circuit): print(" circuit.json MISSING!")
    if not os.path.exists(srs): print(" kzg.srs MISSING!")

    print("\n[7/8] 🔐 Running Setup with Absolute Paths...")
    # Using the exact compiled circuit path
    await safe_ezkl(ezkl.setup, circuit, vk, pk, srs_path=srs)
    print(" Setup Successful!")

    print("\n[8/8] 📜 Generating Smart Contract...")
    await safe_ezkl(ezkl.create_evm_verifier, vk, srs_path=srs, settings_path=settings, sol_code_path=sol, abi_path=abi)
    print("\n=======================================")
    print("✅ SUCCESS! Verifier.sol generated.")
    print("=======================================")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(finalize())
