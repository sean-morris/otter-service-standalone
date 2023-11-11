import tornado
import tornado.ioloop
import tornado.web
import tornado.auth
import os
import uuid
from otter_service_stdalone import fs_logging as log, upload_handle as uh
from zipfile import ZipFile, ZIP_DEFLATED
import asyncio
import async_timeout

__UPLOADS__ = "/tmp/uploads"


class GradeNotebooks():
    """The class contains the async grade method for executing
        otter grader
    """
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
            log.write_logs(results_id, "Step 5: Notebook Folder configured for grader",
                           f"Notebook Folder: {notebook_folder}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            command = [
                'otter', 'grade',
                '-a', p,
                '-p', notebook_folder,
                "--ext", "ipynb",
                "--containers", "10",
                "-o", notebook_folder,
                "-v"
            ]
            log.write_logs(results_id, f"Step 6: Grading Start: {notebook_folder}",
                           " ".join(command),
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
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
                               f'{os.environ.get("ENVIRONMENT")}-debug')
                with open(f"{notebook_folder}/grading-logs.txt", "w") as f:
                    for line in stderr.decode().splitlines():
                        f.write(line + "\n")
                log.write_logs(results_id, "Step 8: Grading: Finished: Write grading-logs.txt",
                               f"{notebook_folder}/grading-logs.txt",
                               "debug",
                               f'{os.environ.get("ENVIRONMENT")}-debug')
                log.write_logs(results_id, f"Step 9: Grading: Finished: {notebook_folder}",
                               " ".join(command),
                               "debug",
                               f'{os.environ.get("ENVIRONMENT")}-debug')
                log.write_logs(results_id, f"Grading: Finished: {notebook_folder}",
                               " ".join(command),
                               "info",
                               f'{os.environ.get("ENVIRONMENT")}-logs')
                return True
        except asyncio.TimeoutError:
            raise Exception(f'Grading timed out for {notebook_folder}')
        except Exception as e:
            raise e


class Userform(tornado.web.RequestHandler):
    """This is the initial landing page for application

    Args:
        tornado (tornado.web.RequestHandler): The request handler
    """
    async def get(self):
        """renders index.html on a GET HTTP request
        """
        self.render("index.html",  message=None)


class Download(tornado.web.RequestHandler):
    """The class handling a request to download results

    Args:
        tornado (tornado.web.RequestHandler): The download request handler
    """
    async def post(self):
        """the post method that accepts the code used to locate the results
        the user wants to download
        """
        code = self.get_argument('download')
        directory = f"{__UPLOADS__}/{code}"
        if code == "":
            log.write_logs(code, "Download: Code Not Given!",
                           f"{code}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            msg = "Please enter the download code to see your result."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}"):
            log.write_logs(code, "Download: Directory for Code Not existing",
                           f"{code}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            msg = "The download code appears to not be correct or expired "
            msg += f"- results are deleted regularly: {code}."
            msg += "Please check the code or upload your notebooks "
            msg += "and autograder.zip for grading again."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}/grading-logs.txt"):
            log.write_logs(code, "Download: Results Not Ready",
                           f"{code}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            msg = "The results of your download are not ready yet. "
            msg += "Please check back."
            self.render("index.html",  download_message=msg, dcode=code)
        else:
            if not os.path.isfile(f"{directory}/final_grades.csv"):
                log.write_logs(code, "Download: final_grades.csv does not exist",
                               "Problem grading notebooks see stack trace",
                               "debug",
                               f'{os.environ.get("ENVIRONMENT")}-debug')
                with open(f"{directory}/final_grades.csv", "a") as f:
                    m = "There was a problem grading your notebooks. Please see grading-logs.txt"
                    f.write(m)
                    f.close()

            log.write_logs(code, "Download Success: Creating results.zip",
                           "",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            with ZipFile(f"{directory}/results.zip", 'w') as zipF:
                for file in ["final_grades.csv", "grading-logs.txt"]:
                    if os.path.isfile(f"{directory}/{file}"):
                        zipF.write(f"{directory}/{file}", file, compress_type=ZIP_DEFLATED)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header("Content-Description", "File Transfer")
            self.set_header('Content-Disposition', f"attachment; filename=results-{code}.zip")
            with open(f"{directory}/results.zip", 'rb') as f:
                try:
                    while True:
                        data = f.read(4096)
                        if not data:
                            break
                        self.write(data)
                    self.finish()
                except Exception as exc:
                    self.write(exc)


class Upload(tornado.web.RequestHandler):
    """This is the upload handler for users to upload autograder.zip and notebooks

    Args:
        tornado (tornado.web.RequestHandler): The upload request handler
    """
    async def post(self):
        """this handles the post request and asynchronously launches the grader
        """
        g = GradeNotebooks()
        files = self.request.files
        results_path = str(uuid.uuid4())
        autograder = self.request.files['autograder'][0] if "autograder" in files else None
        notebooks = self.request.files['notebooks'][0] if "notebooks" in files else None
        log.write_logs(results_path, "Step 1: Upload accepted",
                       "",
                       "debug",
                       f'{os.environ.get("ENVIRONMENT")}-debug')
        if autograder is not None and notebooks is not None:
            notebooks_fname = notebooks['filename']
            notebooks_extn = os.path.splitext(notebooks_fname)[1]
            notebooks_name = results_path + notebooks_extn
            autograder_fname = autograder['filename']
            autograder_extn = os.path.splitext(autograder_fname)[1]
            autograder_name = str(uuid.uuid4()) + autograder_extn
            if not os.path.exists(__UPLOADS__):
                os.mkdir(__UPLOADS__)
            auto_p = f"{__UPLOADS__}/{autograder_name}"
            notebooks_path = f"{__UPLOADS__}/{notebooks_name}"
            log.write_logs(results_path, "Step 2a: Uploaded File Names Determined",
                           f"notebooks path: {notebooks_path}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            fh = open(auto_p, 'wb')
            fh.write(autograder['body'])

            fh = open(notebooks_path, 'wb')
            fh.write(notebooks['body'])
            log.write_logs(results_path, "Step 3: Uploaded Files Written to Disk",
                           f"Results Code: {results_path}",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            m = "Please save this code. You can retrieve your files by submitting this code "
            m += f"in the \"Results\" section to the right: {results_path}"
            self.render("index.html", message=m)
            try:
                await g.grade(auto_p, notebooks_path, results_path)
            except Exception as e:
                log.write_logs(results_path, "Grading Problem",
                               str(e),
                               "error",
                               f'{os.environ.get("ENVIRONMENT")}-logs')
        else:
            log.write_logs(results_path, "Step 2b: Uploaded Files not given",
                           "",
                           "debug",
                           f'{os.environ.get("ENVIRONMENT")}-debug')
            m = "It looks like you did not set the notebooks or autograder.zip or both!"
            self.render("index.html", message=m)


settings = {
    "cookie_secret": str(uuid.uuid4()),
    "xsrf_cookies": True
}

application = tornado.web.Application([
        (r"/", Userform),
        (r"/upload", Upload),
        (r"/download", Download),
        ], **settings, debug=True)


def main():
    """the web servers entry point
    """
    try:
        application.listen(80)
        msg = f'{os.environ.get("ENVIRONMENT")}-debug'
        log.write_logs("Server Start", "Starting Server", "", "info", msg)
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        log.write_logs("Server Start Error", "Server Starting error",
                       str(e),
                       "error",
                       f'{os.environ.get("ENVIRONMENT")}-debug')


if __name__ == "__main__":
    main()
