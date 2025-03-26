import asyncio
import subprocess
import time
from datetime import datetime, timedelta
import json
import aiofiles


async def run_main_with_timeout(duration_minutes):
    """Run main.py for a specified duration"""
    try:
        process = await asyncio.create_subprocess_exec(
            "python",
            "main.py",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        start_time = datetime.now()
        total_seconds = duration_minutes * 60

        # Progress bar task
        async def show_progress():
            while True:
                elapsed = (datetime.now() - start_time).total_seconds()
                progress = min(elapsed / total_seconds, 1.0)
                bar_length = 40
                filled = int(bar_length * progress)
                empty = bar_length - filled
                print(f"\r[{'#' * filled}{' ' * empty}] {int(progress * 100)}%", end="")
                if progress >= 1.0:
                    break
                await asyncio.sleep(1)

        # Create progress bar task
        progress_task = asyncio.create_task(show_progress())

        # Wait for the specified duration
        await asyncio.sleep(total_seconds)

        # Clean up progress bar
        progress_task.cancel()
        print()  # Move to new line after progress bar

        # Send 'stop' command to stdin
        try:
            process.stdin.write(b"stop\n")
            await process.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            pass  # Process might have already terminated

        # Read and print output from main.py
        stdout, stderr = await process.communicate()
        if stdout:
            print(stdout.decode())
        if stderr:
            print(stderr.decode())

        # Wait for process to terminate
        await process.wait()

    except Exception as e:
        print(f"Error during execution: {e}")
    finally:
        # Ensure all resources are properly closed
        if process and process.returncode is None:
            process.terminate()
            await process.wait()

    # Read final position from file
    try:
        with open("final_position.json", "r") as f:
            lines = f.readlines()
            if lines:
                all_positions = [json.loads(line) for line in lines]
                return all_positions
    except FileNotFoundError:
        return []


def reset_inventory():
    """Reset inventory to initial state"""
    inventory = {"Fund": {"USD": 10000000.0}, "BTCUSDT": 0.0}
    with open("inventory.json", "w") as f:
        json.dump(inventory, f)


async def main():
    num_runs = 5
    run_duration = 5  # minutes

    for i in range(num_runs):
        print(f"Starting run {i+1}/{num_runs}")
        start_time = datetime.now()

        # Reset inventory for next run
        reset_inventory()
        print("Inventory reset for the new run\n")
        # Run main.py with timeout
        final_position = await run_main_with_timeout(run_duration)

        # Print results and write to JSON
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        print(f"Run {i+1} completed in {duration} seconds")

        if final_position:
            print(f"Final position: {final_position[-1]}")
            # Write results to JSON file
            result_data = {
                "run_number": i + 1,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration,
                "final_positions": final_position,
            }
            async with aiofiles.open("run_results.jsonl", "a") as f:
                await f.write(json.dumps(result_data) + "\n")

        # Wait 5 seconds before next run
        if i < num_runs - 1:  # Don't wait after the last run
            print("Waiting 5 seconds before next run...")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
