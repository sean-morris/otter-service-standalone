import asyncio
import logging
from otter_service_stdalone import fs_logging as log, upload_handle as uh
import os
from otter.grade import main as grade
from otter import logging as loggers
from multiprocessing import Process
from tornado.ioloop import PeriodicCallback

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

    async def grade(self, p, notebooks_path, image_name, results_id, user_queue):
        """Calls otter grade asynchronously and writes the various log files
        and results of grading generating by otter-grader

        Args:
            p (str): the path to autograder.zip -- the solutions
            notebooks_path (str): the path to the folder of notebooks to be graded\
            image_name (str): the auotgrader.zip file name used as the name for the otter grade docker image
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
            log.write_logs(results_id, "Step 5: Notebook Folder configured and grading started",
                           f"Notebook Folder: {notebook_folder}",
                           "debug",
                           log_debug)
            loggers.set_level(logging.INFO)
            p = Process(target=grade,
                        kwargs = {
                            "name": image_name,
                            "autograder": p,
                            "paths": (notebook_folder,),
                            "containers": 10,
                            "timeout": 1200,
                            "ext": "ipynb",
                            "output_dir": notebook_folder,
                            "result_queue": user_queue,
                            "summaries": True,
                        }
                        )
            p.start()

            # Periodically check if the process is alive
            def check_if_finished():
                if not p.is_alive():
                    log.write_logs(results_id, "Step 6: Grading: Finished",
                                   f"{notebook_folder}",
                                   "debug",
                                   log_debug)
                    log.write_logs(results_id, f"Grading: Finished: {notebook_folder}",
                                   "",
                                   "info",
                                   log_error)
                    periodic_callback.stop()
                    return True

            periodic_callback = PeriodicCallback(check_if_finished, 500)
            periodic_callback.start()

        except asyncio.TimeoutError:
            raise Exception(f'Grading timed out for {notebook_folder}')
        except Exception as e:
            raise e
