import sys, argparse
import src.text_interface
from src.text_interface.text_interface import SMTPClient_CLI
import src.gui
from src.gui.main_ui import SMTPClient_GUI
def runCLI():
    print("Email client start in CLI mode")
    SMTPClient_CLI()

def runGUI():
    print("Email client start in GUI mode")
    program = SMTPClient_GUI()
    program.mainloop()

#If you want to start in CLI mode, run 'main.py -c' or 'main.py --cli'
#If you want to start in GUI mode, run 'main.py -g' or 'main.py --gui'
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cli", help="Run email client on CLI", action="store_true")
    parser.add_argument("-g", "--gui", help="Run email client on GUI", action="store_true")
    args = parser.parse_args()
    if args.cli:
        runCLI()
    elif args.gui:
        runGUI()
    else: #Default this will start in CLI
        runGUI()
    