import os

                                                                   
                                                               

from app import create_app                

                                         
os.environ.setdefault("ENABLE_SCHEDULER", "false")
os.environ.setdefault("ENABLE_FILE_LOGS", "false")
                                                                                  

app = create_app()


