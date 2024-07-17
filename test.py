from otter.grade import main as grade, result_queue as q
import asyncio
import queue


async def grade_notebooks():
    await grade(
        name='wlac',
        autograder="/Users/sean/Desktop/autograder.zip",
        paths=("/Users/sean/Desktop/hw-8-submissions",),
        timeout=1080,
        output_dir="./",
    )


async def process_queue(result_queue):
    while True:
        try:
            results = result_queue.get_nowait()
            print(f"Processing results for {results}")
            result_queue.task_done()
        except queue.Empty:
            await asyncio.sleep(1)  # Sleep for a while before retrying
        await asyncio.sleep(0.1)  # Prevent tight loop


async def main():
    # try:
    grading_tasks = []
    grading_tasks.append(grade_notebooks())
    grading_tasks.append(process_queue(q))
    await asyncio.gather(*grading_tasks)
    # except KeyboardInterrupt:
    #     print("done")
    # except Exception as e:
    #     print(e)

asyncio.run(main())
