import os       
import time     
import pytz
import email
import imghdr
import imaplib
import smtplib
import discord
import picamera
import datetime
import threading
import RPi.GPIO as GPIO
from zipfile import ZipFile
from asyncio.windows_events import NULL

client=discord.Client()
x=0





#pip install python-telegram-bot --upgrade must be done
api_key = os.getenv('api_key')
disc_chk=-1

''' '''



User_Email="srivats.suresh@gmail.com"
# User who's going to control Rpi

Rasp_Email='Raspbian.Raspberry@gmail.com'
# id which Rpi will use to interact with user  

Rasp_Password='rasp123!@#' 
SERVER = 'imap.gmail.com'#
mail = imaplib.IMAP4_SSL(SERVER)
mail.login(Rasp_Email, Rasp_Password)
mail.select('inbox')
# Login into the account and choose inbox

#Declaring global variables which will be accessed and modified across the program
food_interval=8
check_interval=48
mailCheck_interval=2/60

path=''
filename=''
pid=0


#Setting the pin numbers for BCM format
LED_PIN = 17   
LRA_PIN= 25
tankLvl_PIN= 26

# The equivalent physical pin numbers are
# LED_PIN =11
# LRA_PIN =22
#tankLvl_PIN =37

#Setting the pins for input/output
GPIO.setmode(GPIO.BCM)
GPIO.setup(LRA_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)

# Using inbuilt pull-up resistor to keep the pin in HIGH state
GPIO.setup(tankLvl_PIN, GPIO.IN,pull_up_down=GPIO.PUD_UP)


class Email():
    #Class that handles Rpi - User interaction
    
    def Send_Mail(self,content,subject,choice=''):
        #Sends mails with acknowldement, pictures or zip file
        
        #Subject and content of the mail is taken from the parameter
        newMessage = email.message.EmailMessage()                        
        newMessage['Subject'] = subject          #Subject         
        newMessage['From'] = Rasp_Email                 
        newMessage['To'] = User_Email      
        newMessage.set_content(str(content))  #Content 

        if choice=='picture':
            #if choice is picture, attach the picture that was taken latest from the folder

             with open( path,'rb') as f:
                    image_data = f.read()
                    image_type = imghdr.what(f.name)

                    #global variable that has the filename of recently taken picture
                    image_name = filename
                    
                    newMessage.add_attachment(image_data, maintype='image', subtype=image_type, filename=image_name)

        if choice=='album':
            #if choice is album, attach the zip file 
            with open('/media/pi/HP v295w/Aquarium/album.zip','rb') as f:
                    file_data = f.read()
                    file_name ='album.zip'
                    newMessage.add_attachment(file_data, maintype='zip',subtype='', filename=file_name)


        #Login, send the mail and logout   
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(Rasp_Email, Rasp_Password)              
            smtp.send_message(newMessage)
            smtp.quit()



    def Del_Mail(self):
        #Deletes read mails

            #Open all receieved email messages
            status, messages = mail.search(None,'ALL')
            messages = messages[0].split()

            #Individually flag them as '\\Deleted' 
            for num in messages:
                mail.store(num,'+FLAGS','\\Deleted')

            #Delete those flagged mails 
            mail.expunge()
   
             

    
    def Read_Mail(self):
        #Reads mails and cheks the subject for known commands to perform specific tasks

        #if subject is 'STARTSTREAM', call the method that streams live video, with argument 1 
       if(mail.search(None, 'SUBJECT','STARTSTREAM')!=('OK', [b''])):
          Rpi.function.Stream(1)
          
       #if subject is 'FEED', call the method which feeds the fishes
       if(mail.search(None, 'SUBJECT','FEED')!=('OK', [b''])):
          Rpi.function.Feed()
          content='Fishes have been fed successfully'
          subject='Acknowledgement Mail'
          Rpi.interact.Send_Mail(content,subject)

              
       #if subject is 'ALTER', extract and send the mail content to Alter() method                            
       if(mail.search(None, 'SUBJECT','ALTER')!=('OK', [b''])):
          typ, data = mail.search(None, 'SUBJECT','ALTER')
          Rpi.function.Alter(data)
               
       
       #if subject is 'PICTURE', call the SendPic() method  
       if(mail.search(None, 'SUBJECT','PICTURE')!=('OK', [b''])):
         Rpi.function.SendPic()
         content=f'Picture of Aquariam taken at {filename}'
         subject='Picture of aquarium'  
        #Send mail with apropriate subject and content
         Rpi.interact.Send_Mail(content,subject,'picture')
       
       
       #if subject is 'ALBUM', call SendAlbum() method
       if(mail.search(None, 'SUBJECT','ALBUM')!=('OK', [b''])):
         Rpi.function.SendAlbum()
         #Setting the content and subject for mail
         content='Album is attached below for your reference'
         subject='Album file'
         Rpi.interact.Send_Mail(content,subject,'album')

       
       #if subject is 'STOPSTREAM', call the method that streams live video, with argument 0
       if (mail.search(None, 'SUBJECT','STOPSTREAM')!=('OK', [b''])):
          Rpi.function.Stream(0)

       Rpi.interact.Del_Mail()
       #Finally, all mails are deleted after completing the tasks requested in them




class Aquarium_functions():
    #Class that does physical computing and similar actions
   
    def GlowLED(self,i):
        #Glows a LED when photo or video is taken during night time
        
        #Get current date-time for Kolkata and extract time alone from it
        x = datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
        a=int(x.strftime("%H"))


        if i==1:
               if (a>17 or a<6):
                   #If it is after 6pm and before 6am, glow LED 
                   GPIO.output(LED_PIN, GPIO.HIGH)
        else:
            print(123)
            #Switch off LED if i equals 0
            GPIO.output(LED_PIN, GPIO.LOW)
   

    def Stream(self,i):
    # Starts or stops streaming live video in YouTube

        global pid
   
        if i==1:
        # If i==1, enter command to livestream, in terminal

            #Call GlowLED to light up the tank during night
            Rpi.function.GlowLED(1)
            cmd='raspivid -o - -t 0 -vf -hf -fps 30 -b 6000000 | ffmpeg -re -ar 44100 -ac 2 -acodec pcm_s16le -f s16le -ac 2 -i /dev/zero -f h264 -i - -vcodec copy -acodec aac -ab 128k -g 50 -strict experimental -f flv rtmp://a.rtmp.youtube.com/live2/'
            key='mkbc-57cp-cxgf-efsg-a6cm'
            os.popen(cmd+key)

            #Get the process id of the process
            a=os.popen('pidof ffmpeg')
            pid=int(a.readline())
            
        else:
            #if i is 0, stop streaming
            Rpi.function.GlowLED(0)

            #kill the process using its pid
            os.system(f'kill {pid}')
            
                
     
    def checkLevel(self):
        #Checks if water in the tank is above a certain threshold level
    
        if GPIO.input(tankLvl_PIN)!=0:
            content="Water level is low.\n Tank needs to be filled"
            subject="Aquarium water level low "

            #If it's below the required level, notify the user by sending him a mail
            #with the necessary subject and content
            Rpi.interact.Send_Mail(content,subject) 

    def SendPic(self):
    #Takes picture of aquarium and sends it
        
        global path, filename
        
        #Glow LED if it's required
        Rpi.function.GlowLED(1)

        #Prepare Picamera by setting its parameters  
        with picamera.PiCamera() as camera:
            camera.resolution = (1920, 1080)
            camera.start_preview()
            camera.exposure_compensation = 2
           
            # Give the camera some time to adjust to conditions
            time.sleep(2)

            
            #Get current time for naming the pic
            dttime=datetime.datetime.now(pytz.timezone('Asia/Kolkata'))
            dttime=dttime.replace(second=0, microsecond=0)

            #Global variables are altered to be used in Send_Mail() function
            #for retrieving the picture from album
            filename=dttime.strftime ("%Y-%m-%d-%H.%M.%S.jpg")
            path='/media/pi/HP v295w/Aquarium/Album/'+filename
            camera.capture(path)

            #Switch off LED
            Rpi.function.GlowLED(0)
        

    def SendAlbum(self):
    #Sends the entire album containing pictures
        
        #Select a nice name for file and initialize dirName with the path
        with ZipFile('album.zip', 'w') as zipObj:
            dirName='/media/pi/HP v295w/Aquarium/Album'


            # Iterate over all the files in directory
            for folderName, subfolders, filenames in os.walk(dirName):

                for filename in filenames:
                   #create complete filepath of file in directory
                    filePath = os.path.join(folderName, filename)

                    # Add file to zip
                    zipObj.write(filePath,os.path.basename(filePath))

                

             
    def Feed(self):
    #Feeds the fishes by scattering food particles
          
        #Start vibrating the LRA(Linear Resonant Actuator) to which food tray is attached
        GPIO.output(LRA_PIN, GPIO.HIGH)

        #Keep scattering for three seconds to make enough number of particles fall off
        time.sleep(3)

        #Stop vibrating
        GPIO.output(LRA_PIN, GPIO.LOW)

        
        
    
    def Alter(self,data):
    #Alters the inter feeding time and inter water level checking time

        global food_interval, check_interval

        #Traverse through the mails to fetch data and decode 
        data= data[0].split()
        for i in range(len(data[0])): 
            
            for num in data[i].split():
                typ, data = mail.fetch(num, '(RFC822)')
                raw_email = data[i][1]

            #decode the utf-8 format to string
            raw_email_string = raw_email.decode('utf-8')
            b = email.message_from_string(raw_email_string)
              
           
        # If mail contains multiple parts
            if b.is_multipart():
                 for part in b.walk():
                    ctype = part.get_content_type()
                    cdispo = str(part.get('Content-Disposition'))
                
                    #If mail has no attachements and contains only plain text
                    if ctype == 'text/plain' and 'attachment' not in cdispo:
                        body = part.get_payload(decode=True)  # decode
                        print('plain text and no attachements')
                        break
            
             
            else:
                    body = b.get_payload(decode=True)

            body=body.decode('utf-8')           
            l=len(body)

            #Seperating the time and parameter name from body 
            x= body.find(" ")
            body1 =body[0:x]    
            body2=int(body[x+1:l-2])
            print(body1,body2)
        
        
           #If the parameter is food_interval, change it
            subject='Acknowledgement Mail'
            if(body1=='food_interval'):
                food_interval= body2 *60
                print(food_interval)
                content='Food interval has been changed successfully'

            #Else If the parameter is check_interval, change it
            elif (body1=='check_interval'):
                check_interval= body2 *60
                content='Checking interval has been changed successfully'

            #Else it is a wrong scommand     
            else:
                content = "Syntax wrong\n\n Use the correct syntax shown below:\n check_interval <space> <time in hours> (or) food_interval <space> <time in hours>"

             #Send acknowledgement mail accordingly
            Rpi.interact.Send_Mail(content,subject)    


class RaspPi():
 # Class for Raspberry Pi device

    #instance of Email class
    interact = Email()
    #instance of Aquaarium_functions class
    function = Aquarium_functions()
    
#A global instance of RasPi class which is being used to call all the methods 
Rpi = RaspPi()

#discord bot functions below
@client.event
  
async def on_message(message):
    global disc_chk
    global check_interval
    global food_interval
        
    if message.author==client.user:
        return
    
    if message.content.startswith('start stream'):
        Rpi.function.Stream(1)
        await message.channel.send('Check this out 😎: ')
        

    elif  message.content.startswith('Hi'):
        await message.channel.send( "Hello There! 🤖")
         
    elif message.content.startswith('stop stream'):
        await message.channel.send('On it')
        Rpi.function.Stream(0)
        await message.channel.send('Done!')

    elif message.content.startswith('alter food interval'):
        await message.channel.send('Send Interval (in hours):') 
        disc_chk=1        
        
    elif message.content.startswith('alter chk interval'):
        await message.channel.send('Send Interval (in hours):') 
        disc_chk=2
        
    elif disc_chk>0:        
        val=eval(message.content)
        if disc_chk==1:
            food_interval=val*60
            disc_chk=-1
        else:
            check_interval=val*60
            disc_chk=-1


        await message.channel.send('Done! 😊')
        
    elif message.content.startswith('send pic'):
        await message.channel.send('Pic is on the way... 🖼')
        time.sleep(1.5)
        Rpi.function.SendPic()
        with open(path, 'rb') as f:
            picture = discord.File(f)
            await message.channel.send(file=picture)

    elif message.content.startswith('send album'):
        await message.channel.send('Here you go!✨ ')
        Rpi.function.SendAlbum()
        with open('/media/pi/HP v295w/Aquarium/album.zip', 'rb') as f:
            zipfile = discord.File(f)
            await message.channel.send(file=zipfile)

    elif message.content.startswith('check level'):
        if GPIO.input(tankLvl_PIN)!=0:
          await message.channel.send('Water level is low❗\n Tank needs to be filled')
                                   
        
    elif message.content.startswith('feed now'):
        await message.channel.send('Feeding the fishes...')
        Rpi.function.Feed()
        await message.channel.send('Done!')
                                   
    else:
        await message.channel.send('Try AGain!')
#End of discord bot functions

 
def discord_bot():
    global food_interval
    client.run('OTQ2MjczMDg4NjU4NjIwNDI4.YhcTfQ.3zOIAiQxdUkDZxOMeBBh0DJXEbM')
    



#Main function
def main():
    #Timers for fish-feeding, tank level checking and mail-checking,
    food_reference_time=time.time()
    check_reference_time=time.time()
    mail_reference_time=time.time()
    curr_time=time.time()
    try:
        while(True):
        #Keep doing all the time
            curr_time=time.time()
            if(curr_time - food_reference_time > food_interval * 60):
                
            #If the fish feed timer has crossed the food_interval, feed the fishes
                Rpi.function.Feed()


                #Reset the fish_feed timer
                food_reference_time=time.time()
            
            
            curr_time=time.time()
            if(curr_time - check_reference_time > check_interval * 60):
            #If the tank level check timer has crossed the check_interval, call checkLevel function
                Rpi.function.checkLevel()
                

                #Reset the tank level check timer
                check_reference_time=time.time()            
             
            curr_time=time.time()
            if(curr_time - mail_reference_time > mailCheck_interval * 60):
            #If the mail check timer has crossed the mailCheck_interval,
            #go and check inbox for any new mail from user  
            
                Rpi.interact.Read_Mail()
                mail_reference_time=time.time()              
     
    except KeyboardInterrupt:
                p1.terminate()
        #If an unexpected interrupt occurs 

                
                #close and logout from mail server
                mail.close()
                mail.logout()
    finally:
         GPIO.cleanup()
        
# To allow main() function to get executed only when this
# program is run directly


if __name__ == "__main__":

    # starting processes
    p2=threading.Thread(target=discord_bot)
    p2.start()
    main()


                    

    
