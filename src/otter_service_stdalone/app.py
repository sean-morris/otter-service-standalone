import tornado
import tornado.ioloop
import tornado.web
import tornado.auth
import os
import uuid
import tornado.websocket
from otter_service_stdalone import fs_logging as log
from otter_service_stdalone import user_auth as u_auth
from otter_service_stdalone import grade_notebooks
from zipfile import ZipFile, ZIP_DEFLATED
import queue


__UPLOADS__ = "/tmp/uploads"
log_debug = f'{os.environ.get("ENVIRONMENT")}-debug'
log_error = f'{os.environ.get("ENVIRONMENT")}-logs'
log_http = f'{os.environ.get("ENVIRONMENT")}-http-error'

authorization_states = {}  # used to protect against cross-site request forgery attacks.
session_queues = {}
session_messages = {}
session_callbacks = {}


class WebSocketHandler(tornado.websocket.WebSocketHandler):
    """This handles updates to the application from otter-grader
    """
    def open(self):
        """if logged in, start a callback once a second to see if there messages for the
            logged in user
        """
        if self.get_secure_cookie("user"):
            user_id = self.get_secure_cookie("user").decode('utf-8')
            if user_id not in session_callbacks:
                session_callbacks[user_id] = tornado.ioloop.PeriodicCallback(lambda: self.send_results(user_id), 1000)
                session_callbacks[user_id].start()

    def on_message(self, message):
        pass  # No action needed on incoming message

    def on_close(self):
        """stop the periodic classback on close
        """
        close_code = self.close_code
        close_reason = self.close_reason
        log.write_logs("socket", close_code, f"{close_code}: {close_reason}", "debug", log_debug)
        if self.get_secure_cookie("user"):
            user_id = self.get_secure_cookie("user").decode('utf-8')
            if user_id in session_callbacks and session_callbacks[user_id].callback:
                session_callbacks[user_id].stop()
                session_callbacks.pop(user_id)

    def send_results(self, user_id):
        """if there are messages for this user, send them to application by submission.
            We save the messages in the session so if refresh on client side they still
            have the updates
        """
        try:
            if user_id in session_queues:
                user_queue_dict = session_queues[user_id]
                user_messages_dict = session_messages[user_id]
                if user_queue_dict:
                    for result_id, q in user_queue_dict.items():
                        if not q.empty():
                            while not q.empty():
                                user_messages_dict[result_id].append(q.get())
                            self.write_message({"messages": user_messages_dict})
        except tornado.websocket.WebSocketClosedError:
            log.write_logs("ws-error", "Web Socket Problem", "", "", log_error)


class HealthHandler(tornado.web.RequestHandler):
    """Handles Load Balancer Health Check

    Args:
        tornado (tornado.web.RequestHandler): The request handler
    """
    def get(self):
        self.set_status(200)


class LoginHandler(tornado.web.RequestHandler):
    """Initiaties login auth by authorizing access to github auth api

    Args:
        tornado (tornado.web.RequestHandler): The request handler
    """
    async def get(self):
        state = str(uuid.uuid4())
        authorization_states[state] = True
        await u_auth.handle_authorization(self, state)


class BaseHandler(tornado.web.RequestHandler):
    """This is the super class for the handlers. get_current_user is called by
    any handler that decorated with @tornado.web.authenticated

    Args:
        tornado (tornado.web.RequestHandler): The request handler
    """
    def get_current_user(self):
        return self.get_secure_cookie("user")

    def write_error(self, status_code, **kwargs):
        log.write_logs("Http Error", f"{status_code} Error", "", "info", log_http)
        self.clear_cookie("user")
        if status_code == 403:
            self.set_status(403)
            self.render("static_templates/403.html", support=f'{os.environ.get("SUPPORT_EMAIL")}')
        else:
            self.set_status(500)
            self.render("static_templates/500.html", support=f'{os.environ.get("SUPPORT_EMAIL")}')


class GitHubOAuthHandler(BaseHandler):
    """Handles GitHubOAuth

    Args:
        tornado (tornado.web.RequestHandler): The request handler
    """
    async def get(self):
        code = self.get_argument('code', False)
        arg_state = self.get_argument('state', False)
        if arg_state not in authorization_states:
            m = "UserAuth: GitHubOAuthHandler: Cross-Site Forgery possible - aborting"
            log.write_logs("Auth Workflow", m, "", "info", log_error)
            log.write_logs("Auth Workflow", m, "", "info", log_debug)
            raise tornado.web.HTTPError(500)

        del authorization_states[arg_state]

        access_token = await u_auth.get_acess_token(code)
        if access_token is None:
            raise tornado.web.HTTPError(403)

        user = await u_auth.get_github_username(access_token)
        if not user:
            raise tornado.web.HTTPError(403)

        is_org_member = await u_auth.handle_is_org_member(access_token, user)
        if not is_org_member:
            raise tornado.web.HTTPError(403)

        self.set_secure_cookie("user", user, expires_days=7)
        self.redirect("/")


class MainHandler(BaseHandler):
    """This is the initial landing page for application

    Args:
        BaseHandler (BaseHandler): super class
    """
    @tornado.web.authenticated
    async def get(self):
        self.render("index.html", message=None)


class Download(BaseHandler):
    """The class handling a request to download results

    Args:
        tornado (tornado.web.RequestHandler): The download request handler
    """
    @tornado.web.authenticated
    def get(self):
        # this just redirects to login and displays main page
        self.render("index.html", message=None)

    @tornado.web.authenticated
    async def post(self):
        """the post method that accepts the code used to locate the results
        the user wants to download
        """
        download_code = self.get_argument('download')
        directory = f"{__UPLOADS__}/{download_code}"
        if download_code == "":
            m = "Download: Code Not Given!"
            log.write_logs(download_code, m, f"{download_code}", "debug", log_debug)
            msg = "Please enter the download code to see your result."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}"):
            m = "Download: Directory for Code Not existing"
            log.write_logs(download_code, m, f"{download_code}", "debug", log_debug)
            msg = "The download code appears to not be correct or expired "
            msg += f"- results are deleted regularly: {download_code}."
            msg += "Please check the code or upload your notebooks "
            msg += "and autograder.zip for grading again."
            self.render("index.html",  download_message=msg)
        elif not os.path.exists(f"{directory}/final_grades.csv"):
            m = "Download: Results Not Ready"
            log.write_logs(download_code, m, f"{download_code}", "debug", log_debug)
            msg = "The results of your download are not ready yet. "
            msg += "Please check back."
            self.render("index.html",  download_message=msg, dcode=download_code)
        else:
            m = "Download Success: Creating results.zip"
            log.write_logs(download_code, m, "", "debug", log_debug)
            with ZipFile(f"{directory}/results.zip", 'w') as zipF:
                final_file = "final_grades.csv"
                if os.path.isfile(f"{directory}/{final_file}"):
                    zipF.write(f"{directory}/{final_file}", final_file, compress_type=ZIP_DEFLATED)
                for filename in os.listdir(f"{directory}/grading-summaries"):
                    file_path = os.path.join(f"{directory}/grading-summaries", filename)
                    if os.path.isfile(file_path):
                        f_path = f"grading-summaries-do-not-distribute/{filename}"
                        zipF.write(f"{file_path}", f_path, compress_type=ZIP_DEFLATED)
                read_me = os.path.join(os.path.dirname(__file__), "static_files", "README_DO_NOT_DISTRIBUTE.txt")
                zipF.write(read_me, "README_DO_NOT_DISTRIBUTE.txt", compress_type=ZIP_DEFLATED)

            self.set_header('Content-Type', 'application/octet-stream')
            self.set_header("Content-Description", "File Transfer")
            m = f"attachment; filename=results-{download_code}.zip"
            self.set_header('Content-Disposition', m)
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


class Upload(BaseHandler):
    """This is the upload handler for users to upload autograder.zip and notebooks

    Args:
        tornado (tornado.web.RequestHandler): The upload request handler
    """        
    @tornado.web.authenticated
    def get(self):
        # this just redirects to login and displays main page
        self.render("index.html", message=None)

    @tornado.web.authenticated
    async def post(self):
        """this handles the post request and asynchronously launches the grader
        """
        user = self.get_current_user()
        user_id = user.decode('utf-8')
        if user_id not in session_queues:
            session_queues[user_id] = {}
            session_messages[user_id] = {}
        g = grade_notebooks.GradeNotebooks()
        files = self.request.files
        results_path = str(uuid.uuid4())
        autograder = self.request.files['autograder'][0] if "autograder" in files else None
        notebooks = self.request.files['notebooks'][0] if "notebooks" in files else None
        log.write_logs(results_path, "Step 1: Upload accepted", "", "debug", log_debug)
        if autograder is not None and notebooks is not None:
            notebooks_fname = notebooks['filename']
            notebooks_extn = os.path.splitext(notebooks_fname)[1]
            if notebooks_extn == ".zip":
                notebooks_name = results_path + notebooks_extn
            else:
                notebooks_name = f"{results_path}/{notebooks_fname}"
                os.mkdir(f"{__UPLOADS__}/{results_path}")
            autograder_fname = autograder['filename']
            autograder_extn = os.path.splitext(autograder_fname)[1]
            autograder_name = str(uuid.uuid4()) + autograder_extn
            if not os.path.exists(__UPLOADS__):
                os.mkdir(__UPLOADS__)
            auto_p = f"{__UPLOADS__}/{autograder_name}"
            notebooks_path = f"{__UPLOADS__}/{notebooks_name}"
            m = "Step 2a: Uploaded File Names Determined"
            log.write_logs(results_path, m, f"notebooks path: {notebooks_path}", "debug", log_debug)
            fh = open(auto_p, 'wb')
            fh.write(autograder['body'])

            fh = open(notebooks_path, 'wb')
            fh.write(notebooks['body'])
            m = "Step 3: Uploaded Files Written to Disk"
            log.write_logs(results_path, m, f"Results Code: {results_path}", "debug", log_debug)
            m = "Please save this code; it appears in the \"Notebook Grading Progress\" section below. You can "
            m += f"retrieve your files by submitting this code in the \"Results\" section to the right: {results_path}"
            self.render("index.html", message=m)
            try:
                session_queues[user_id][results_path] = queue.Queue()
                session_messages[user_id][results_path] = []
                await g.grade(auto_p, notebooks_path, results_path, session_queues[user_id].get(results_path))
            except Exception as e:
                log.write_logs(results_path, "Grading Problem", str(e), "error", log_error)
        else:
            m = "Step 2b: Uploaded Files not given"
            log.write_logs(results_path, m, "", "debug", log_debug)
            m = "It looks like you did not set the notebooks or autograder.zip or both!"
            self.render("index.html", message=m)


settings = {
    "cookie_secret": str(uuid.uuid4()),
    "xsrf_cookies": True,
    "login_url": "/login"
}

application = tornado.web.Application([
        (r"/", MainHandler),
        (r"/login", LoginHandler),
        (r"/upload", Upload),
        (r"/download", Download),
        (r"/update", WebSocketHandler),
        (r"/oauth_callback", GitHubOAuthHandler),
        (r"/otterhealth", HealthHandler),
        (r"/scripts/(.*)", tornado.web.StaticFileHandler, {"path": os.path.join(os.path.dirname(__file__), "scripts")}),
        ], **settings, debug=False)


def main():
    """the web servers entry point
    """
    try:
        application.listen(80)
        log.write_logs("Server Start", "Starting Server", "", "info", log_debug)
        tornado.ioloop.IOLoop.instance().start()
    except Exception as e:
        m = "Server Starting error"
        log.write_logs("Server Start Error", m, str(e), "error", log_debug)


if __name__ == "__main__":
    main()
