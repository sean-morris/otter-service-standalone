import asyncio
import async_timeout
from otter_service_stdalone import fs_logging as log, upload_handle as uh
import os

log_debug = f'{os.environ.get("ENVIRONMENT")}-debug'
log_count = f'{os.environ.get("ENVIRONMENT")}-count'
log_error = f'{os.environ.get("ENVIRONMENT")}-logs'


class GradeNotebooks():
    """The class contains the async grade method for executing
        otter grader as well as a function for logging the number of 
        notebooks to be graded
    """

    def count_ipynb_files(self, directory, extension):
        """this count the files for logging purposes"""
        count = 0
        for filename in os.listdir(directory):
            if filename.endswith(extension):
                count += 1
        return count

    async def grade(self, p, notebooks_path, results_id):
        """Calls otter grade asynchronously and writes the various log files
        and results of grading generating by otter-grader

        Args:
            p (str): the path to autograder.zip -- the solutions
            notebooks_path (str): the path to the folder of notebooks to be graded
            results_id (str): used for identifying logs

        Raises:
            Exception: Timeout Exception is raised if async takes longer than 20 min

        Returns:
            boolean: True is the process completes; otherwise an Exception is thrown
        """
        try:
            notebook_folder = uh.handle_upload(notebooks_path, results_id)
            notebook_count = self.count_ipynb_files(notebook_folder, ".ipynb")
            log.write_logs(results_id, f"{notebook_count}",
                           "",
                           "info",
                           f'{os.environ.get("ENVIRONMENT")}-count')
            log.write_logs(results_id, "Step 5: Notebook Folder configured for grader",
                           f"Notebook Folder: {notebook_folder}",
                           "debug",
                           log_debug)
            command = [
                'otter', 'grade',
                '-n', 'grader',
                '-a', p,
                notebook_folder,
                "--ext", "ipynb",
                "--containers", "10",
                "--timeout", "1080",
                "-o", notebook_folder,
                "-v"
            ]
            log.write_logs(results_id, f"Step 6: Grading Start: {notebook_folder}",
                           " ".join(command),
                           "debug",
                           log_debug)
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # this is waiting for communication back from the process
            # some images are quite big and take some time to build the first
            # time through - like 20 min for otter-grader
            async with async_timeout.timeout(2000):
                stdout, stderr = await process.communicate()

                with open(f"{notebook_folder}/grading-output.txt", "w") as f:
                    for line in stdout.decode().splitlines():
                        f.write(line + "\n")
                log.write_logs(results_id, "Step 7: Grading: Finished: Write: grading-output.txt",
                               f"{notebook_folder}/grading-output.txt",
                               "debug",
                               log_debug)
                with open(f"{notebook_folder}/grading-logs.txt", "w") as f:
                    for line in stderr.decode().splitlines():
                        f.write(line + "\n")
                log.write_logs(results_id, "Step 8: Grading: Finished: Write grading-logs.txt",
                               f"{notebook_folder}/grading-logs.txt",
                               "debug",
                               log_debug)
                log.write_logs(results_id, f"Step 9: Grading: Finished: {notebook_folder}",
                               " ".join(command),
                               "debug",
                               log_debug)
                log.write_logs(results_id, f"Grading: Finished: {notebook_folder}",
                               " ".join(command),
                               "info",
                               log_error)
                return True
        except asyncio.TimeoutError:
            raise Exception(f'Grading timed out for {notebook_folder}')
        except Exception as e:
            raise e
