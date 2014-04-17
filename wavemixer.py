from gi.repository import Gtk, GObject
import sys,wave,struct,os,time,signal,pyaudio
MAX16=32767
MIN16=-32768
MAX8=127
MIN8=-128
from recordit import *

class play:
    def __init__(self,file):
        self.chunk=1024
        self.file=file
        self.p=False

    def playit(self):
        spf = wave.open(self.file, 'rb')
        p=pyaudio.PyAudio()
        stream=p.open(format=p.get_format_from_width(spf.getsampwidth()),
                           channels=spf.getnchannels(),
                           rate=spf.getframerate(),
                           output=True)

        data=spf.readframes(self.chunk)

        while data!='':
            if(not self.p):
                stream.write(data)
                data = spf.readframes(self.chunk)
        stream.close()
        p.terminate()

class wav:
    def __init__(self):
        self.amp=1
        self.tsh=0
        self.tsc=1
        self.rev=0
        self.mod=0
        self.mix=0
        self.file="NONE"
        self.play="NONE"
        self.data=[]
        self.state=-1
        self.no_channels=0
        self.samplewidth=0
        self.framerate=0
        self.no_frames=0
    def read(self):
        wavf = wave.open(self.file, 'r')
        no_channels=wavf.getnchannels()
        samplewidth=wavf.getsampwidth()
        framerate=wavf.getframerate()
        no_frames=wavf.getnframes()
        r = wavf.readframes( no_frames )
        total_samples = no_frames * no_channels
        if samplewidth == 1:
            fmt = "%iB" % total_samples
        elif samplewidth == 2:
            fmt = "%ih" % total_samples
        inw = struct.unpack(fmt, r)
        data=[]
        for i in inw:
            data.append(i)
        self.data=data
        self.no_channels=no_channels
        self.samplewidth=samplewidth
        self.framerate=framerate
        self.no_frames=no_frames
        wavf.close()

    def amplify(self):
        data=self.data
        amp=self.amp
        if(self.samplewidth==1):
            for i in range(len(data)):
                x=data[i]
                x=x-128
                y=x*amp
                if(y>=MIN8 and y<=MAX8):
                    data[i]=y
                elif (y>MAX8):
                    data[i]=MAX8
                elif (y<MIN8):
                    data[i]=MIN8
                data[i]+=128
        else:
            for i in range(len(data)):
                x=data[i]
                y=x*amp
                if(y>=MIN16 and y<=MAX16):
                    data[i]=y
                elif (y>MAX16):
                    data[i]=MAX16
                elif (y<MIN16):
                    data[i]=MIN16
        self.data=data
    def timeshift(self):
        tsh=self.tsh
        if self.no_channels==1:
            if(tsh>0):
                self.data=self.data[int(self.framerate*tsh):]
                self.no_frames=len(self.data)
            elif(tsh<0):
                t=[]
                tsh=(-1)*tsh
                for i in range(int(self.framerate*tsh)):
                    t.append(0)
                t.extend(self.data)
                self.data=t
                self.no_frames=len(self.data)
        else:
            if(tsh>0):
                self.data=self.data[int(self.framerate*tsh*2):]
                self.no_frames=len(self.data)/2
            elif(tsh<0):
                tsh=(-2)*tsh
                t=[]
                for i in range(int(self.framerate*tsh)):
                    t.append(0)
                t.extend(self.data)
                self.data=t
                self.no_frames=len(self.data)/2
        return
    def timescaling(self):
        #print "timescaling"
        if(self.no_channels==1):
            #print "1234778"
            t=[]
            tsc=(self.tsc)*1.0
            fac=0.0
            while(fac<len(self.data)):
                if fac.is_integer():
                    i=int(fac)
                    t.append(self.data[i])
                else:
                    t.append(0)
                fac=fac+tsc
            self.data=t
            self.no_frames=len(self.data)
        else:
            l=self.data[::2]
            r=self.data[1::2]
            t=[]
            tsc=self.tsc*1.0
            fac=0.0
            while(fac<len(self.data)):
                if fac.is_integer():
                    i=int(fac)
                    t.append(self.data[i])
                else:
                    t.append(0)
                fac=fac+tsc
            l=t
            t=[]
            tsc=self.tsc*1.0
            fac=0.0
            while(fac<len(self.data)):
                if isinstance(fac,int):
                    t.append(self.data[fac])
                else:
                    t.append(0)
                fac=fac+tsc
            r=t
            self.data=[]
            for i in range(len(l)):
                self.data.append(l[i])
                self.data.append(r[i])
            self.no_frames=len(self.data)/2

    def reverse(self):
        print "not reversing"
        print self.rev
        if self.rev == 1:
            print "reversing"
            if self.no_channels==1:
                self.data=list(reversed(self.data))
            elif(self.no_channels==2):
                l=list(self.data[::2])
                r=list(self.data[1::2])
                l=list(reversed(l))
                r=list(reversed(r))
                self.data=[]
                for i in range(self.no_frames):
                    self.data.append(l[i])
                    self.data.append(r[i])
        return

    def write(self):
        data=self.data
        #attributes=self.attributes
        #samplewidth=self.attributes["samplewidth"]
        total_samples = self.no_frames * self.no_channels
        if self.samplewidth == 1:
            fmt = "%iB" % total_samples
        else:
            fmt = "%ih" % total_samples
        f=struct.pack(fmt,*data)
        wav = wave.open(self.play,"w")
        wav.setnchannels(self.no_channels)
        wav.setframerate(self.framerate)
        wav.setsampwidth(self.samplewidth)
        wav.setnframes(self.no_frames)
        wav.writeframes(f)
        wav.close()


class wave_mixer(Gtk.Window):
    def __init__(self):
        
        #self.connect("destroy",self.endprogram)
        self.playing=False
        self.playid=0
        self.whichplayed=0
        self.pasttime=[]
        self.time=[]
        for i in range(5):
            self.pasttime.append(0)
            self.time.append(time.time())
        #hseparator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        #vseparator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self.filelabel=list()
        #image_m = Gtk.Image()
        Gtk.Window.__init__(self, title="Wave Mixer")
        grid = Gtk.Grid()
        self.add(grid)
        self.filelabel.append(Gtk.Label("No File Chosen",xalign=0))
        self.filelabel.append(Gtk.Label("No File Chosen",xalign=0))
        self.filelabel.append(Gtk.Label("No File Chosen",xalign=0))
        button1 = Gtk.Button("Choose File")
        button1.connect("clicked", self.on_file_clicked,0)
        button2 = Gtk.Button("Choose File")
        button2.connect("clicked", self.on_file_clicked,1)
        button3 = Gtk.Button("Choose File")
        button3.connect("clicked", self.on_file_clicked,2)

        grid.attach(button1,0,0,1,1)
        grid.attach(self.filelabel[0],1,0,1,1)
        grid.attach(button2,2,0,1,1)
        grid.attach(self.filelabel[1],3,0,1,1)
        grid.attach(button3,4,0,1,1)
        grid.attach(self.filelabel[2],5,0,1,1)

        label=Gtk.Label("Amplitude",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,0,1,1,1)


        ad1 = Gtk.Adjustment(1, 0, 8, 5, 10, 0)
        self.h_scale_amp1 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_amp1.set_digits(1)
        self.h_scale_amp1.set_hexpand(True)
        self.h_scale_amp1.set_valign(Gtk.Align.START)
        self.h_scale_amp1.connect("value-changed", self.scale_moved,0)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_amp1, 0, 2, 1, 1)

        label=Gtk.Label("Amplitude",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,2,1,1,1)
        ad1 = Gtk.Adjustment(1, 0, 8, 5, 10, 0)
        self.h_scale_amp2 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_amp2.set_digits(1)
        self.h_scale_amp2.set_hexpand(True)
        self.h_scale_amp2.set_valign(Gtk.Align.START)
        self.h_scale_amp2.connect("value-changed", self.scale_moved,1)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_amp2, 2, 2, 1, 1)

        label=Gtk.Label("Amplitude",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,4,1,1,1)
        ad1 = Gtk.Adjustment(1, 0, 8, 5, 10, 0)
        self.h_scale_amp3 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_amp3.set_digits(1)
        self.h_scale_amp3.set_hexpand(True)
        self.h_scale_amp3.set_valign(Gtk.Align.START)
        self.h_scale_amp3.connect("value-changed", self.scale_moved,2)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_amp3, 4, 2, 1, 1)


        label=Gtk.Label("Time Shift",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,0,4,1,1)
        ad1 = Gtk.Adjustment(0, -1, 1, 5, 10, 0)
        self.h_scale_tsh1 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsh1.set_digits(2)
        self.h_scale_tsh1.set_hexpand(True)
        self.h_scale_tsh1.set_valign(Gtk.Align.START)
        self.h_scale_tsh1.connect("value-changed", self.scale_moved ,3)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsh1, 0, 5, 1, 1)


        label=Gtk.Label("Time Shift",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,2,4,1,1)
        ad1 = Gtk.Adjustment(0, -1, 1, 5, 10, 0)
        self.h_scale_tsh2 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsh2.set_digits(2)
        self.h_scale_tsh2.set_hexpand(True)
        self.h_scale_tsh2.set_valign(Gtk.Align.START)
        self.h_scale_tsh2.connect("value-changed", self.scale_moved,4)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsh2, 2, 5, 1, 1)

        label=Gtk.Label("Time Shift",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,4,4,1,1)
        ad1 = Gtk.Adjustment(0, -1, 1, 5, 10, 0)
        self.h_scale_tsh3 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsh3.set_digits(2)
        self.h_scale_tsh3.set_hexpand(True)
        self.h_scale_tsh3.set_valign(Gtk.Align.START)
        self.h_scale_tsh3.connect("value-changed", self.scale_moved,5)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsh3, 4, 5, 1, 1)

        label=Gtk.Label("Time Scaling",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,0,7,1,1)
        ad1 = Gtk.Adjustment(1, 0, 5, 5, 10, 0)
        self.h_scale_tsc1 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsc1.set_digits(2)
        self.h_scale_tsc1.set_hexpand(True)
        self.h_scale_tsc1.set_valign(Gtk.Align.START)
        self.h_scale_tsc1.connect("value-changed", self.scale_moved,6)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsc1, 0, 8, 1, 1)


        label=Gtk.Label("Time Scaling",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,2,7,1,1)
        ad1 = Gtk.Adjustment(1, 0, 5, 5, 10, 0)
        self.h_scale_tsc2 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsc2.set_digits(2)
        self.h_scale_tsc2.set_hexpand(True)
        self.h_scale_tsc2.set_valign(Gtk.Align.START)
        self.h_scale_tsc2.connect("value-changed", self.scale_moved,7)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsc2, 2, 8, 1, 1)

        label=Gtk.Label("Time Scaling",xalign=0)
        label.set_justify(Gtk.Justification.LEFT)
        grid.attach(label,4,7,1,1)
        ad1 = Gtk.Adjustment(1, 0, 5, 5, 10, 0)
        self.h_scale_tsc3 = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=ad1)
        self.h_scale_tsc3.set_digits(2)
        self.h_scale_tsc3.set_hexpand(True)
        self.h_scale_tsc3.set_valign(Gtk.Align.START)
        self.h_scale_tsc3.connect("value-changed", self.scale_moved,8)
        self.label = Gtk.Label()
        self.label.set_text("Move the scale handles...")
        grid.attach(self.h_scale_tsc3, 4, 8, 1, 1)

        button_rev1 = Gtk.CheckButton()
        button_rev1.set_label("Time Reversal")
        button_rev1.connect("toggled", self.on_button_toggled, 0)
        #button_rev3.set_active(True)
        grid.attach(button_rev1,0,9,1,1)

        button_mod1 = Gtk.CheckButton()
        button_mod1.set_label("Select For Modulation")
        button_mod1.connect("toggled", self.on_button_toggled, 3)
        #button_rev3.set_active(True)
        grid.attach(button_mod1,0,10,1,1)

        button_mix1 = Gtk.CheckButton()
        button_mix1.set_label("Select For Mixing")
        button_mix1.connect("toggled", self.on_button_toggled, 6)
        #button_rev3.set_active(True)
        grid.attach(button_mix1,0,11,1,1)

        button_rev2 = Gtk.CheckButton()
        button_rev2.set_label("Time Reversal")
        button_rev2.connect("toggled", self.on_button_toggled, 1)
        #button_rev3.set_active(True)
        grid.attach(button_rev2,2,9,1,1)

        button_mod2 = Gtk.CheckButton()
        button_mod2.set_label("Select For Modulation")
        button_mod2.connect("toggled", self.on_button_toggled, 4)
        #button_rev3.set_active(True)
        grid.attach(button_mod2,2,10,1,1)

        button_mix2 = Gtk.CheckButton()
        button_mix2.set_label("Select For Mixing")
        button_mix2.connect("toggled", self.on_button_toggled, 7)
        #button_rev3.set_active(True)
        grid.attach(button_mix2 ,2,11,1,1)


        button_rev3 = Gtk.CheckButton()
        button_rev3.set_label("Time Reversal")
        button_rev3.connect("toggled", self.on_button_toggled, 2)
        #button_rev3.set_active(True)
        grid.attach(button_rev3,4,9,1,1)

        button_mod3 = Gtk.CheckButton()
        button_mod3.set_label("Select For Modulation")
        button_mod3.connect("toggled", self.on_button_toggled, 5)
        #button_rev3.set_active(True)
        grid.attach(button_mod3,4,10,1,1)

        button_mix3 = Gtk.CheckButton()
        button_mix3.set_label("Select For Mixing")
        button_mix3.connect("toggled", self.on_button_toggled, 8)
        #button_rev3.set_active(True)
        grid.attach(button_mix3,4,11,1,1)

        self.box = Gtk.Box(spacing=6)

        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
        self.button_play1 = Gtk.Button(halign=1,valign=1)
        self.button_play1.connect("clicked", self.play, 0)
        self.button_play1.set_image(image)
        self.box.pack_start(self.button_play1, True, True, 0)
        grid.attach(self.box,0,12,1,1)
        # create a progress bar
        self.progressbar1 = Gtk.ProgressBar()
        self.box.pack_start(self.progressbar1, True, True, 0)
        #grid.attach(self.progressbar,0,13,1,1)


        self.box = Gtk.Box(spacing=6)
        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
        self.button_play2 = Gtk.Button(halign=1,valign=1)
        self.button_play2.connect("clicked", self.play, 1)
        self.button_play2.set_image(image)
        self.box.pack_start(self.button_play2, True, True, 0)
        grid.attach(self.box,2,12,1,1)
        # create a progress bar
        self.progressbar2 = Gtk.ProgressBar()
        self.box.pack_start(self.progressbar2, True, True, 0)
        #grid.attach(self.progressbar,0,13,1,1)

        self.box = Gtk.Box(spacing=6)
        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
        self.button_play3 = Gtk.Button(halign=1,valign=1)
        self.button_play3.connect("clicked", self.play, 2)
        self.button_play3.set_image(image)
        self.box.pack_start(self.button_play3, True, True, 0)
        grid.attach(self.box,4,12,1,1)
        # create a progress bar
        self.progressbar3 = Gtk.ProgressBar()
        self.box.pack_start(self.progressbar3, True, True, 0)
        #grid.attach(self.progressbar,0,13,1,1)

        self.box = Gtk.Box(spacing=6)
        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
        self.button_play4 = Gtk.Button(halign=1,valign=1)
        self.button_play4.connect("clicked", self.play, 3)
        self.button_play4.set_image(image)
        self.box.pack_start(self.button_play4, True, True, 0)
        label_mod = Gtk.Label(label="Modulate And Play")
        grid.attach(self.box,1,13,1,1)
        grid.attach(label_mod,1,14,1,1)
        # create a progress bar
        self.progressbar4 = Gtk.ProgressBar()
        self.box.pack_start(self.progressbar4, True, True, 0)

        self.box = Gtk.Box(spacing=6)
        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
        self.button_play5 = Gtk.Button(halign=1,valign=1)
        self.button_play5.connect("clicked", self.play, 4)
        self.button_play5.set_image(image)
        self.box.pack_start(self.button_play5, True, True, 0)
        grid.attach(self.box,3,13,1,1)
        label_mix = Gtk.Label(label="Mix And Play")
        grid.attach(label_mix,3,14,1,1)
        # create a progress bar
        self.progressbar5 = Gtk.ProgressBar()
        self.box.pack_start(self.progressbar5, True, True, 0)
        
        
        self.box1 = Gtk.Box(spacing=6)
        image = Gtk.Image(stock=Gtk.STOCK_MEDIA_RECORD)
        self.button_record = Gtk.Button(halign=1,valign=1)
        self.button_record.set_image(image)
        self.button_record.connect("clicked", self.recording)
        self.recordlabel=Gtk.Label("Record in myrecording.wav",xalign=0)
        self.box1.pack_start(self.button_record, True, True, 0)
        #self.box1.pack_start(self.recordlabel, True, True, 0)
        grid.attach(self.box1,2,15,1,1)
        grid.attach(self.recordlabel,2,16,1,1)
        

        self.progressbar=[]
        self.progressbar.append(self.progressbar1)
        self.progressbar.append(self.progressbar2)
        self.progressbar.append(self.progressbar3)
        self.progressbar.append(self.progressbar4)
        self.progressbar.append(self.progressbar5)

        self.timeout_id = GObject.timeout_add(100, self.on_timeout, self.progressbar)
        self.activity_mode = False

    def recording(self,widget):
        rid=os.fork()
        if(rid==0):
            record_to_file("myrecording.wav")
            sys.exit(0)
        return
    def on_timeout(self, user_data):
        """
        Update value on the progress bar
        """
        for i in range(5):
            if(wavlist[i].state==1 and wavlist[i].no_frames!=0):
                user_data[i].set_fraction(((self.pasttime[i]+time.time()-self.time[i])*wavlist[i].framerate)/(wavlist[i].no_frames))
                if (((self.pasttime[i]+time.time()-self.time[i])*wavlist[i].framerate)/(wavlist[i].no_frames))>=1:
                    user_data[i].set_fraction(0)
                    wavlist[i].state=-1
                    image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
                    if(i==0):
                        self.button_play1.set_image(image)
                    if(i==1):
                        self.button_play2.set_image(image)
                    if(i==2):
                        self.button_play3.set_image(image)
                    if(i==3):
                        self.button_play4.set_image(image)
                    if(i==4):
                        self.button_play5.set_image(image)
            elif(wavlist[i].state==-1):
                user_data[i].set_fraction(0)

        # As this is a timeout function, return True so that it
        # continues to get called
        return True
    def endprogram(self,widget,data=None):
        if(self.playid!=0 and self.playing):
            os.kill(self.playid,9)
        Gtk.main_quit(self,widget)
    
    def on_button_pressed(self, widget):
        self.progressbar.set_fraction(0.0)
        frac = 1.0 / 1000
        for i in range(0,100):
            new_val = self.progressbar.get_fraction() + frac
            #print new_val, f
            self.progressbar.set_fraction(new_val)
        return True

    def onplay(self,n):
        print n
        if(self.playid!=0 and self.playing):
            self.time[n]=time.time()
            self.pasttime[n]=0
            os.kill(self.playid,9)
            self.playing=False
            wavlist[self.whichplayed].state=-1
            self.playid=0
            image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
            if(self.whichplayed==0):
                self.button_play1.set_image(image)
            if(self.whichplayed==1):
                self.button_play2.set_image(image)
            if(self.whichplayed==2):
                self.button_play3.set_image(image)
            if(self.whichplayed==3):
                self.button_play4.set_image(image)
            if(self.whichplayed==4):
                self.button_play5.set_image(image)
            self.onplay(n)
        else:
            if(n<3):
                wavlist[n].read()
                wavlist[n].amplify()
                wavlist[n].timeshift()
            #print "asanka"+str(wavlist[n].rev)
                wavlist[n].timescaling()
                wavlist[n].reverse()
            else:
                for i in range(3):
                    if(wavlist[i].mix or wavlist[i].mod):
                        wavlist[i].read()
                        wavlist[i].amplify()
                        wavlist[i].timeshift()
            #print "asanka"+str(wavlist[n].rev)
                        wavlist[i].timescaling()
                        wavlist[i].reverse()
                if(n==3):
                    wavlist[3].data=[]
                    t=[]
                    for i in range(3):
                        if(wavlist[i].mod==1):
                            t.append(wavlist[i])
                    #print t
                    m=len(t[0].data)
                    for i in range(len(t)-1):
                        b=max(len(t[i].data),len(t[i+1].data))
                        m=max(m,b)
                    for i in range(m):
                        x=1.0
                        for j in range(len(t)):
                            if(i<len(t[j].data)):
                                if(t[j].samplewidth==1):
                                    x=x*(t[j].data[i]-128)
                                else:
                                    x=x*(t[j].data[i])
                        if(t[0].samplewidth==2):
                            if(x>MAX16):
                                x=MAX16
                            elif(x<MIN16):
                                x=MIN16
                        else:
                            if(x>MAX8):
                                x=MAX8
                            elif(x<MIN8):
                                x=MIN8
                        #print m,i,x
                        if(t[0].samplewidth==1):
                            x=x+128
                        wavlist[3].data.append(x)
                    wavlist[3].samplewidth=t[0].samplewidth
                    wavlist[3].framerate=t[0].framerate
                    wavlist[3].no_channels=t[0].no_channels
                    if(t[0].no_channels==2):
                        wavlist[3].no_frames=len(wavlist[3].data)/2
                    if(t[0].no_channels==1):
                        wavlist[3].no_frames=len(wavlist[3].data)
                    #wavlist[3].mod()
                elif(n==4):
                    wavlist[4].data=[]
                    t=[]
                    for i in range(3):
                        if(wavlist[i].mix==1):
                            t.append(wavlist[i])
                    m=len(t[0].data)
                    f=1.0/len(t)
                    for i in range(len(t)-1):
                        b=max(len(t[i].data),len(t[i+1].data))
                        m=max(m,b)
                    for i in range(m):
                        x=0.0
                        for j in range(len(t)):
                            if(i<len(t[j].data)):
                                x=x+(f*t[j].data[i])
                        #print t[0].samplewidth
                        if(t[0].samplewidth==2):
                            if(x>MAX16):
                                x=MAX16
                            elif(x<MIN16):
                                x=MIN16
                        else:
                            if(x>255):
                                x=255
                            elif(x<0):
                                x=0
                        wavlist[4].data.append(x)
                    wavlist[4].samplewidth=t[0].samplewidth
                    wavlist[4].framerate=t[0].framerate
                    wavlist[4].no_channels=t[0].no_channels
                    if(wavlist[4].no_channels==1):
                        wavlist[4].no_frames=len(wavlist[4].data)
                    else:
                        wavlist[4].no_frames=len(wavlist[4].data)/2
            file=""
            file+="out"
            file+=str(n)
            file+=".wav"
            print file
            wavlist[n].play=file
            wavlist[n].write()
            self.time[n]=time.time()
            self.pasttime[n]=0
            self.whichplayed=n
            for j in range(5):
                if(j!=n):
                    self.time[j]=0
            newpid=os.fork()
            if(newpid==0):
                p=play(wavlist[n].play)
                p.playit()
                parentid=os.getppid()
                os.kill(parentid,signal.SIG_IGN)
                sys.exit(0)
            self.playing=True
            self.playid=newpid

    def play(self,widget,n):
        print wavlist[n].state
        if wavlist[n].state==1:
            image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY)
            widget.set_image(image)
            wavlist[n].state=0
            if(self.playid!=0):
                self.pasttime[n]+=time.time()-self.time[n]
                self.time[n]=0
                os.kill(self.playid,signal.SIGSTOP)
        elif wavlist[n].state==0:
            image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PAUSE)
            widget.set_image(image)
            print n
            wavlist[n].state=1
            if(self.playid!=0):
                self.time[n]=time.time()
                os.kill(self.playid,signal.SIGCONT)
        else:
            image = Gtk.Image(stock=Gtk.STOCK_MEDIA_PAUSE)
            widget.set_image(image)
            wavlist[n].state=1
            self.onplay(n)

    def on_button_toggled(self, button, n):
        if button.get_active():
            print "ON"
            if(n>=0 and n<3):
                wavlist[n].rev=1
            elif(n>=3 and n<6):
                wavlist[n-3].mod=1
            elif(n>=6 and n<9):
                wavlist[n-6].mix=1
        else:
            print "OFF"
            if(n>=0 and n<3):
                wavlist[n].rev=0
            elif(n>=3 and n<6):
                wavlist[n-3].mod=0
            elif(n>=6 and n<9):
                wavlist[n-6].mix=0

    def on_file_clicked(self, widget,no):
        dialog = Gtk.FileChooserDialog("Please choose a file", self,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
             Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
        self.add_filters(dialog)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            fileselected= dialog.get_filename()
            wavlist[no].file=fileselected
            fileselected=fileselected.split("/")
            self.filelabel[no].set_label(fileselected[-1])
        elif response == Gtk.ResponseType.CANCEL:
            print("Cancel clicked")
        dialog.destroy()

    def scale_moved(self, event,n):
        if(n>=0 and n<3):
            wavlist[n].amp=event.get_value()
        elif(n>=3 and n<6):
            wavlist[n-3].tsh=event.get_value()
        elif(n>=6 and n<9):
            wavlist[n-6].tsc=event.get_value()

    def add_filters(self, dialog):
        filter_text = Gtk.FileFilter()
        filter_text.add_pattern("*.wav")
        filter_text.add_pattern("*.WAV")
        dialog.add_filter(filter_text)

wavlist=[]
wavlist.append(wav())
wavlist.append(wav())
wavlist.append(wav())
wavlist.append(wav())
wavlist.append(wav())
window = wave_mixer()
window.set_icon_from_file('web.jpg')
def signal_handler(singal,frame):
    os.waitpid(-1,0)
    window.playing=False
signal.signal(signal.SIG_IGN, signal_handler)
window.connect("delete-event", Gtk.main_quit)
#exit_status = window.run(sys.argv)
#sys.exit(exit_status)
window.show_all()
Gtk.main()
