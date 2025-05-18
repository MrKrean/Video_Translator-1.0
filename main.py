import os
import logging
import contextlib
from ui.main import VideoTranslatorApp

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.CRITICAL,
        handlers=[],
        force=True
    )
    
    with open(os.devnull, 'w') as devnull:
        with contextlib.redirect_stdout(devnull), contextlib.redirect_stderr(devnull):
            app = VideoTranslatorApp()
            app.mainloop()