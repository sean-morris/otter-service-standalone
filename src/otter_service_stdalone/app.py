import tornado
import tornado.ioloop
import tornado.web
import tornado.auth
import os, uuid
from subprocess import run
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
from otter_service_stdalone import fs_logging as log
from zipfile import ZipFile, ZIP_DEFLATED
import asyncio
import async_timeout

__UPLOADS__ = "/tmp/uploads"

class GradeNotebooks():
    async def grade(self, p, notebooks_zip):
        try:
            zip_folder = notebooks_zip.split(".")[0]
            with ZipFile(notebooks_zip, 'r') as zObject:
                zObject.extractall(path=zip_folder)
            
            command = [
                'otter', 'grade',
                '-a', p,
                '-p', zip_folder,
                "--ext", "ipynb", 
                "-o", zip_folder, 
                "-v"
            ]
            log.write_logs(f"Grading: Start: {zip_folder}", " ".join(command), "info", f'{os.environ.get("ENVIRONMENT")}-logs')
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
            
            log.write_logs(f"Grading: Finished: {zip_folder}", "", "info", f'{os.environ.get("ENVIRONMENT")}-logs')
            
            for line in stderr.decode('utf-8').split('\n'):
                if line.strip() == '':
                    # Ignore empty lines
                    continue
                if 'Killed' in line:
                    # Our container was killed, so let's just skip this one
                    raise Exception(f"Container was killed -- nothing will work")

            with open(f"{zip_folder}/grading-output.txt", "w") as f:
                for line in stdout.decode().splitlines():
                    f.write(line + "\n")
            
            with open(f"{zip_folder}/grading-logs.txt", "w") as f:
                for line in stderr.decode().splitlines():
                    f.write(line  + "\n")
        except asyncio.TimeoutError:
            raise Exception(f'Grading timed out for {zip_folder}')
        except Exception as e:
            raise e  
        return "Grading Done"

class Userform(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html",  message=None)

class Download(tornado.web.RequestHandler):
    async def post(self):
        code = self.get_argument('download')
        directory = f"{__UPLOADS__}/{code}"
        if code == "":
            msg = f"Please enter the download code to see your result."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}"):
            msg = f"The download code appears to not be correct or expired - results are deleted each night: {code}. Please check the code or upload your notebooks and autograder.zip for grading again."
            self.render("index.html",  download_message=msg)
        elif not os.path.isfile(f"{directory}/final_grades.csv"):
            msg = f"The results of your download are not ready yet. Please check back: {code}"
            self.render("index.html",  download_message=msg)
        else:
            with ZipFile(f"{directory}/results.zip", 'w') as zipF:
                for file in ["final_grades.csv","grading-output.txt","grading-logs.txt"]:
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
    async def post(self):
        g = GradeNotebooks()
        files = self.request.files
        autograder = self.request.files['autograder'][0] if "autograder" in files else None
        notebooks = self.request.files['notebooks'][0] if "notebooks" in files else None
        if autograder is not None and notebooks is not None:
            print("fileinfo is: ", autograder)
            notebooks_fname = notebooks['filename']
            notebooks_extn = os.path.splitext(notebooks_fname)[1]
            results_path = str(uuid.uuid4())
            notebooks_name = results_path + notebooks_extn

            autograder_fname = autograder['filename']
            autograder_extn = os.path.splitext(autograder_fname)[1]
            autograder_name = str(uuid.uuid4()) + autograder_extn
            if not os.path.exists(__UPLOADS__):
                os.mkdir(__UPLOADS__)
            auto_p = f"{__UPLOADS__}/{autograder_name}"
            notebook = f"{__UPLOADS__}/{notebooks_name}"
            fh = open(auto_p, 'wb')
            fh.write(autograder['body'])
            
            fh = open(notebook, 'wb')
            fh.write(notebooks['body'])
            
            m = f"Please save this code. You can retrieve your files by submitting this code in the \"Results\" section to the right: {results_path}"
            self.render("index.html", message=m)
            try:
                await g.grade(auto_p, notebook)
            except Exception as e:
                log.write_logs("Grading Problem", str(e), "error", f'{os.environ.get("ENVIRONMENT")}-logs')
        else:
            m = f"It looks like you did not set one of the upload zip files."
            self.render("index.html", message=m)
        
settings = {
    "cookie_secret": str(uuid.uuid4())
}
application = tornado.web.Application([
        (r"/", Userform),
        (r"/upload", Upload),
        (r"/download", Download),
        ], **settings, debug=True)

def main():
    try:
        application.listen(80)
        log.write_logs("Starting Server", "", "info", f'{os.environ.get("ENVIRONMENT")}-logs')
        tornado.ioloop.IOLoop.instance().start()
        
    except Exception as e:
        log.write_logs("Server Starting error", str(e), "error", f'{os.environ.get("ENVIRONMENT")}-logs')

if __name__ == "__main__":
    main()