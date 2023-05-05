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
from kivy.core.image import Image as CoreImage
from kivy.uix.image import Image as kiImage
from kivy.clock import Clock
from PIL import Image

from KivyOnTop import register_topmost, unregister_topmost

from pynput import mouse
from io import BytesIO

class step:
    """
    Empire AI step protocol 0.1
    Inputs step('''xxx''', tries=3, timer=1, gate=1, bbox=None)
    Output step.locations (tuples of x,y in screen space)
    
    """
    def __init__(self, payload, tries=3, timer=1, gate=1, bbox=None, kill_on_fail=True, autoexec=True):
        self.payloads = dill.loads(codecs.decode(payload.encode(), "base64"))
        self.pattern_img = self.payloads[0]
        self.offset = self.payloads[1]
        self.kill_on_fail = kill_on_fail
        self.version = 0.2
        self.tries = tries
        self.gate = gate
        self.timer = timer
        self.kill_on_fail = kill_on_fail
        if autoexec:
            self.search()
    
    def search(self):
        # Try to find the pattern
        for counter in range(self.tries):
            self._find_()
            # If enough instances have been found break out of the loop and execute next cell
            if len(self.locations) >= self.gate:
                print("found: "+str(self.locations))
                break
            else:
                time.sleep(self.timer)
        
        # If the pattern is not found within timeout
        if len(self.locations) < self.gate:
            #pr.style={'bar_color': '#800000'}
            #pl.value="[STOPPED] could not find"
            print("EXCEPTION: Gate condition not met!")
            if self.kill_on_fail:
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
            self.app.status_label.text = 'Paused' 
            self.app.status = 'pasued'
            self.text = 'Play'
        elif self.app.status == 'paused':
            self.app.status_label.text = 'Started' 
            # for some reason I could not use gui.getAllWindiwByTitle
            gui.hotkey('alt','tab')
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
        # ToDo: clean this up
        self.instruction_img = None
        # 
        self.playback_button = controllerButton(self,text="Play",size_hint=(1,.6))
        # start timer for updatimg the
        
        def _run_stack(dt):
            """
            Function to run throught the stack once, while making it possible to pause at every step
            """
            if self.command_index == len(self.commands):
                self.status = 'stopped'
                self.playback_button.text = 'Stopped'
                self.playback_button.disabled = True
                return
            if self.status == 'paused':
                return
            
            try:
                command = self.commands[self.command_index]
                exec(command[0],globals(),locals())
                self.update_step_preview(image=self.s.payloads[3])
            except Exception as e:
                print(e)              
            # Try to find the pattern on the screen
            try:
                exec(command[1],globals(),locals())
            except Exception as e:
                print(e)
                
            # update done list
            self.command_index += 1
            # update progress bar
            self.progressbar.value = self.command_index/len(self.commands)*100
            self.progressbar_label.text = str(round(self.progressbar.value))+"%"            
            
        self.clock = Clock.schedule_interval(_run_stack,1)
        
    
    def on_start(self, *args):
        Window.set_title("runner")
        register_topmost(Window,"runner")
        
    
    def update_step_preview(self, image=False):
        print(str(image))
        if image==False:
            self._image = Image.new('RGB', (320,320), color=(128,0,0))
            self.img_widget = kiImage()
        else:
            self._image = image
        data = BytesIO()
        self._image.save(data,format='png')
        data.seek(0)
        self.coreimage_texture = CoreImage(BytesIO(data.read()), ext='png')
        self.img_widget.texture = self.coreimage_texture.texture
        
    def build(self):
        self.window = GridLayout(cols=1,padding=(10,10,10,10))
        
        # Add Widgets
        self.status_label = Label(text="ready to test")
        #self.status_label = Label(text="paused", valign='top')
        #self.status_label.bind(size=self.status_label.setter('text_size')) 
        self.window.add_widget(self.status_label)
        self.current_step = 0
        self.script_running = False
        
        # generate blank place holder for image to be loaded
        blank_image = Image.new('RGB', (320,320), color=(128,0,0))
        self.img_widget = kiImage(size_hint=(1,1))
        self.update_step_preview(image=blank_image)
        
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
        self.progressbar = ProgressBar(max=100, value=0, size_hint=(0.7,1))
        self.progress.add_widget(self.progressbar)
        self.progressbar_label = Label(text="0%", size_hint=(0.3,1) )
        self.progress.add_widget(self.progressbar_label)
        self.progress.add_widget(ProgressBar(max=1, value=0, size_hint=(0.7,1)))
        self.progress.add_widget(Label(text="0/1", size_hint=(0.3,1) ))
        self.window.add_widget(self.progress)   
        
        self.window.add_widget(Label(text="step:"))
        self.window.add_widget(self.img_widget)
        self.window.add_widget(Label(text="variables:"))
        self.window.add_widget(TextInput(text="comment: Looks like you're ready to capture the perfect shot with that lighting setup!", size_hint=(1,2)))
        
        Window.size = (400,800)
        
        return self.window

r = runnerUI()
r.run()