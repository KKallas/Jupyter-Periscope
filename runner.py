import pyautogui as gui
import codecs
import dill
import time
import threading

from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.textinput import TextInput
from kivy.core.window import Window

from KivyOnTop import register_topmost, unregister_topmost

from pynput import mouse

class step:
    """
    Empire AI step protocol 0.1
    Inputs step('''xxx''', tries=3, timer=1, gate=1, bbox=None)
    Output step.locations (tuples of x,y in screen space)
    
    """
    def __init__(self, payload, tries=3, timer=1, gate=1, bbox=None, kill_on_fail=True):
        self.payloads = dill.loads(codecs.decode(payload.encode(), "base64"))
        self.pattern_img = self.payloads[0]
        self.offset = self.payloads[1]
        self.kill_on_fail = kill_on_fail
        self.version = 0.1
        
        # Try to find the pattern
        for counter in range(tries):
            self._find_()
            # If enough instances have been found break out of the loop and execute next cell
            if len(self.locations) >= gate:
                print("found: "+str(self.locations))
                break
            else:
                time.sleep(timer)
        
        # If the pattern is not found within timeout
        if len(self.locations) < gate:
            #pr.style={'bar_color': '#800000'}
            #pl.value="[STOPPED] could not find"
            print("EXCEPTION: Gate condition not met!")
            if kill_on_fail:
                #pr.style={'bar_color': '#808000'}
                raise Exception("Gate condition not met!")
        
    def _find_(self):
        """
        Find pattern on the screen as many instances as possible
        save all found locations into self.locations with correct click offset
        """
        
        self.locations = []
        locations_found = gui.locateAllOnScreen(self.pattern_img)
        offset = self.payloads[1]
        
        for loc in locations_found:
            self.locations.append((loc.left+offset[0],loc.top+offset[1]))
            
# later replace with string at the moemnt importing from file as thonny has hard time with the ultra long lines
import workflow
workflow = workflow.workflow

class controllerButton(Button):
    """
    Customization of the default class to have acess to app
    in the 'on_press' event
    """
    def __init__(self, myself, **kwargs):
        super(controllerButton, self).__init__(**kwargs)
        self.app = myself
        
    def on_press(self):
        """
        Toggle between play and pause
        """
        if self.app.status == 'playing':
            self.app.paused = True
            self.app.status = 'pasued'
            self.text = 'Play'
        elif self.app.status == 'paused':
            # for some reason I could not use gui.getAllWindiwByTitle
            gui.hotkey('alt','tab')
            self.app.paused = False
            self.app.status = 'playing'
            self.text = 'Pause'          

class runnerUI(App):
    """
    Kivy app instance for the local script runner (self contaioned) app
    """
    def __init__(self, **kwargs):
        """
        Setup local variables to control the playback/pause and UI of the front-end
        """
        super(runnerUI,self).__init__(**kwargs)
        
        self.status = 'paused'
        self.commands = workflow
        self.command_index = 0
        self.paused = True
        self.disabled = False
        # 
        self.playback_button = controllerButton(self,text="Play",size_hint=(1,.6))
        # start the backend thread
        self.thread = threading.Thread(target=self._run_stack)
        self.thread.start()
        
    def _run_stack(self):
        """
        Function to run throught the stack once, while making it possible to pause at every step
        """
        while self.command_index < len(self.commands):
            if self.paused:
                time.sleep(1)
            else:
                command = self.commands[self.command_index]
                try:
                    exec(command,globals(),locals())
                except Exception as e:
                    print(e)
                    time.sleep(1)
                # update done list
                self.command_index += 1
                # update progress bar
                self.progressbar.value = self.command_index/len(self.commands)*100
                self.progressbar_label.text = str(round(self.progressbar.value))+"%"
            
        self.status = 'stopped'
        self.playback_button.text = 'Stopped'
        self.playback_button.disabled = True 
        
    
    def on_start(self, *args):
        Window.set_title("runner")
        register_topmost(Window,"runner")
        
    def build(self):
        self.window = GridLayout(cols=1,padding=(10,10,10,10))
        
        # Add Widgets
        self.status_label = Label(text="ready to test")
        #self.status_label = Label(text="paused", valign='top')
        #self.status_label.bind(size=self.status_label.setter('text_size')) 
        self.window.add_widget(self.status_label)
        self.current_step = 0
        self.script_running = False
        
        

        # 
        def on_move(x, y):
            # pause playback if mause is moved
            if self.status == 'playing':
                self.status = 'paused'
                self.paused = True
                self.playback_button.text = 'Play'
                
        self.mouselistener = mouse.Listener(on_move=on_move)
        self.mouselistener.start()
        """    
            current_step = App.get_running_app().current_step
            while current_step < len(workflow):
                self.status_label.text = str(current_step)
                exec(workflow[self.current_step],globals(),locals())
                current_step = current_step + 1
                App.get_running_app().current_step = current_step
            self.mouselistener.stop()
        """    
 
        self.window.add_widget(self.playback_button)
        
        self.progress = GridLayout(cols=2)
        self.progressbar = ProgressBar(max=100, value=20, size_hint=(0.7,1))
        self.progress.add_widget(self.progressbar)
        self.progressbar_label = Label(text="0%", size_hint=(0.3,1) )
        self.progress.add_widget(self.progressbar_label)
        self.progress.add_widget(ProgressBar(max=1, value=1, size_hint=(0.7,1)))
        self.progress.add_widget(Label(text="1/1", size_hint=(0.3,1) ))
        self.window.add_widget(self.progress)   
        
        self.window.add_widget(Label(text="variables:"))
        
        self.window.add_widget(TextInput(text="comment: Looks like you're ready to capture the perfect shot with that lighting setup!", size_hint=(1,3)))
        
        Window.size = (400,600)
        
        return self.window

r = runnerUI()
r.run()