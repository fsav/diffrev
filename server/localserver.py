# Simple server to handle more advanced reviewing functionality
# (up to now all you couldn't _write to DB_ at all from the browser-based
# review pages, so this is a post-hoc design change to allow more flexibility)

# using tutorial at
# http://blog.doughellmann.com/2007/12/pymotw-basehttpserver.html

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import urlparse
import json

if __name__ == '__main__':
    # otw when running tests we can't import other modules
    this_files_path = os.path.split(os.path.abspath(__file__))[0]
    sys.path.append(os.path.join(this_files_path,".."))

from core.storage import Storage, Revision

SERVER_PORT = 3546

# see set_global_storage... this is an ugly hack but I couldn't figure out a
# better way with BaseHTTPRequestHandler and HTTPServer
# (well, I gave up after searching for half an hour, so if you've got time take
# a shot)
_GLOBAL_STORAGE = None

# LOCAL is very important: this has NO SECURITY AT ALL so don't configure this
# to accept connections from anything else than localhost!
class LocalReviewServer(BaseHTTPRequestHandler):

    # This is super ugly, but I couldn't figure out how to inherit from the superclass
    # _and_ override __init__ while passing the _class_ (not _instance_)
    # to the HTTPServer call.
    @staticmethod
    def set_global_storage(storage):
        global _GLOBAL_STORAGE
        assert _GLOBAL_STORAGE is None
        _GLOBAL_STORAGE = storage

    def do_GET(self):
        parsed_path = urlparse.urlparse(self.path)
        
        path_without_qs = parsed_path.path

        query_string_dict = urlparse.parse_qs(parsed_path.query)

        if path_without_qs in ("/hidereview", "/hidereview/"):
            self.do_hidereview(query_string_dict)

        elif path_without_qs in ("/dumpreview", "/dumpreview/"):
            self.do_dumpreview(query_string_dict)

        elif path_without_qs in ("/debug", "/debug/"):
            self.do_debug()

        else:
            self.send_response(404)
            self.end_headers()

        return

    def do_dumpreview(self, query_string_dict):
        global _GLOBAL_STORAGE

        review_id = int(query_string_dict['reviewid'][0])
        review_obj = Revision.get_revision_from_id(_GLOBAL_STORAGE, review_id)

        self.send_response(200)
        self.end_headers()
        
        self.wfile.write(str(review_obj))

    def do_hidereview(self, query_string_dict):
        global _GLOBAL_STORAGE

        review_id = int(query_string_dict['reviewid'][0])
        review_obj = Revision.get_revision_from_id(_GLOBAL_STORAGE, review_id)

        review_obj.set_hidden_state(True)

        self.send_response(200)
        self.end_headers()

        result_obj = { 'operation': 'hidereview',
                       'review_id': review_obj.id,
                       'review_path': review_obj.document_relative_path,
                       'result': 'ok' }
        
        self.wfile.write(json.dumps(result_obj))

    def do_debug(self):
        parsed_path = urlparse.urlparse(self.path)

        message = '\n'.join([
                'CLIENT VALUES:',
                'client_address=%s (%s)' % (self.client_address,
                                            self.address_string()),
                'command=%s' % self.command,
                'path=%s' % self.path,
                'real path=%s' % parsed_path.path,
                'query=%s' % urlparse.parse_qs(parsed_path.query),
                'request_version=%s' % self.request_version,
                '',
                'SERVER VALUES:',
                'server_version=%s' % self.server_version,
                'sys_version=%s' % self.sys_version,
                'protocol_version=%s' % self.protocol_version,
                '',
                ]) 

        self.send_response(200)
        self.end_headers()
        # self.wfile wraps the response socket
        self.wfile.write(message)

if __name__ == '__main__':
    server = HTTPServer(('localhost', SERVER_PORT), LocalReviewServer)
    print 'Starting server, use <Ctrl-C> to stop'
    server.serve_forever()

