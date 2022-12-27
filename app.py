import tornado
import tornado.ioloop
import tornado.web
import os, uuid
from subprocess import run
from tornado.concurrent import Future
from tornado.httpclient import AsyncHTTPClient
from zipfile import ZipFile, ZIP_DEFLATED


__UPLOADS__ = "uploads"

class GradeNotebooks():
    def async_upload(url):
        http_client = AsyncHTTPClient()
        my_future = Future()
        fetch_future = http_client.fetch(url)
        def on_fetch(f):
            my_future.set_result(f.result().body)
        fetch_future.add_done_callback(on_fetch)
        return my_future

    async def grade(self, p, notebooks_zip):
        zip_folder = notebooks_zip.split(".")[0]
        with ZipFile(notebooks_zip, 'r') as zObject:
            zObject.extractall(path=zip_folder)
        out = run(["otter", "grade", "-a", p, "-p", zip_folder, "--ext", "ipynb", "-o", zip_folder, "-v"], capture_output=True)
        with open(f"{zip_folder}/grading-output.txt", "w") as f:
            for line in out.stdout.decode().splitlines():
                f.write(line + "\n")
        
        with open(f"{zip_folder}/grading-logs.txt", "w") as f:
            for line in out.stderr.decode().splitlines():
                f.write(line  + "\n")
        return "Grading Done"

class Userform(tornado.web.RequestHandler):
    def get(self):
        self.render("index.html",  message=None)


class Upload(tornado.web.RequestHandler):
    def download(self, code):
        directory = f"{__UPLOADS__}/{code}"
        if not os.path.exists(f"{directory}"):
            msg = f"The download code appears to not be correct or expired - results are deleted each night: {code}. Please check the code or upload your notebooks and autograder.zip for grading again."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}/final_grades.csv"):
            msg = "The results of your download are not ready yet. Please check back."
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

    
    async def post(self):
        g = GradeNotebooks()
        files = self.request.files
        autograder = self.request.files['autograder'][0] if "autograder" in files else None
        notebooks = self.request.files['notebooks'][0] if "notebooks" in files else None
        download_code = self.get_argument('download')
        if download_code:
            self.download(download_code)
        elif autograder is not None and notebooks is not None:
            print("fileinfo is: ", autograder)
            notebooks_fname = notebooks['filename']
            notebooks_extn = os.path.splitext(notebooks_fname)[1]
            results_path = str(uuid.uuid4())
            notebooks_name = results_path + notebooks_extn

            autograder_fname = autograder['filename']
            autograder_extn = os.path.splitext(autograder_fname)[1]
            autograder_name = str(uuid.uuid4()) + autograder_extn
            auto_p = f"{__UPLOADS__}/{autograder_name}"
            notebook = f"{__UPLOADS__}/{notebooks_name}"
            fh = open(auto_p, 'wb')
            fh.write(autograder['body'])
            
            fh = open(notebook, 'wb')
            fh.write(notebooks['body'])
            
            self.render("index.html", message=f"You can retrieve your files by submitting this code below: {results_path}")
            return_msg = await g.grade(auto_p, notebook)
            print(return_msg)
            
        


application = tornado.web.Application([
        (r"/", Userform),
        (r"/upload", Upload),
        ], debug=True)


if __name__ == "__main__":
    application.listen(8888)
    tornado.ioloop.IOLoop.instance().start()