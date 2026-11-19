# Upstream login server the proxy forwards to. For a fully local run, point it
# at the mock login server (see run_mock.py).
LOGIN_HOST = ""
LOGIN_PORT = 443

# Where the proxy listens. The client must point at LOCAL_HOST:LOCAL_LOGIN_PORT.
LOCAL_HOST = "127.0.0.1"
LOCAL_LOGIN_PORT = 4430
LOCAL_GAME_PORT = 5555

# Folder for packet logs (one file per connection).
LOG_DIR = "logs"

# Also echo every packet to the console.
ECHO_TO_CONSOLE = True

# Local mock server (mock_server.py / run_mock.py). To test the proxy against
# the simulated servers: LOGIN_HOST = "127.0.0.1" and LOGIN_PORT = the mock
# login port. The proxy ports can remain 4430/5555.
MOCK_LOGIN_PORT = 14430
MOCK_GAME_PORT = 15555
