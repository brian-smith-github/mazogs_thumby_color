# MAZOGS - A MAZE ADVENTURE GAME
# Original version by Don Priestley (RIP). Bonsai porting by Brian Smith.

import engine_main

import engine
import engine_io
import engine_draw
from engine_nodes import Sprite2DNode, CameraNode
from engine_resources import TextureResource

import framebuf
import random
import gc
import math
import time
from random import random
from random import randint
from random import seed
from defines import *
from tiles24x16 import *
from tiles4x4 import *
from glfont import *

tiles_big=bytearray(2210)
tiles_small=bytearray(100)
font=bytearray(1280)

for i in range(0, 2208):
  tiles_big[i]=tiles24x16[i]
for i in range(0,49):
  tiles_small[i]=tiles4x4[i]
for i in range(0,1280):
  font[i]=glfont[i]  
 
maze=bytearray(2816) # 64x44


maze_number=1
posn=0
counter=0
counter2=0
random8bit=0
pose=STILL
frame=0
move_frame=0 # character movelent frame bit
carrying=HAVE_NOTHING
level=1
moves_left=0
initial_moves=0
kill_moves=0


#-------------------------------------------------------------
@micropython.viper
def grey_screen():
    pos=0
    # Viper pointers for quick access to the buffers
    buf = ptr16(engine_draw.back_fb_data())
    for x in range(0,128):
      for y in range(0,128):
        if x&0b1:
	  if y&0b1:
            buf[pos]=65535
          else:
            buf[pos]=0
	else:
	  if y&0b1:
	    buf[pos]=0
	  else:
	    buf[pos]=65535
        pos+=1

#-----------------------------------------------------------
@micropython.viper
def black_screen():
  buf = ptr16(engine_draw.back_fb_data())
  for pos in range(0,128*128):
    buf[pos]=0


#--------------------------------------------------------------
@micropython.viper
def print_char(c:int, xx:int, yy:int, inv:int):
   # Viper pointers for quick access to the buffers
   buf = ptr16(engine_draw.back_fb_data())
   t=ptr8(font)
   posn=yy*128
   posn+=xx
   for x in range(0,6):
     if x==5: a=0
     else: a=t[c*5+x]
     if inv==0: a=a^0b11111111
     for y in range(0,8):
       if a & 0b1 : buf[posn]=65535
       else: buf[posn]=0
       a>>=1; posn+=128
     posn-=128*8; posn+=1;

#--------------------------------------------------------------
# test double-hight font
@micropython.viper
def print_char2(c:int, xx:int, yy:int, inv:int):
   # Viper pointers for quick access to the buffers
   buf = ptr16(engine_draw.back_fb_data())
   t=ptr8(font)
   if yy>112: yy=112
   posn=yy*128
   posn+=xx
   for x in range(0,6):
     if x==5: a=0
     else: a=t[c*5+x]
     if inv==0: a=a^0b11111111
     for y in range(0,8):
       if a & 0b1 : buf[posn]=65535; buf[posn+128]=65535
       else: buf[posn]=0; buf[posn+128]=0
       a>>=1; posn+=256
     posn-=256*8; posn+=1;
     
#--------------------------------------------------------------
# test double-hight,double-width font
@micropython.viper
def print_char3(c:int, xx:int, yy:int, inv:int):
   # Viper pointers for quick access to the buffers
   buf = ptr16(engine_draw.back_fb_data())
   t=ptr8(font)
   if yy>112: yy=112
   posn=yy*128
   posn+=xx
   for x in range(0,6):
     if x==5: a=0
     else: a=t[c*5+x]
     if inv==0: a=a^0b11111111
     for y in range(0,8):
       if a & 0b1 : buf[posn]=65535; buf[posn+128]=65535; \
                    buf[posn+1]=65535; buf[posn+129]=65535
       else: buf[posn]=0; buf[posn+128]=0; \
             buf[posn+1]=0; buf[posn+129]=0
       a>>=1; posn+=256
     posn-=256*8; posn+=2;


#--------------------------------------------------------------
def printt(x,y,string,inv):
  s=list(string)
  for c in s:
    print_char2(ord(c),x,y,inv)
    x+=6   
#--------------------------------------------------------------
def printt2(x,y,string,inv):
  s=list(string)
  for c in s:
    print_char3(ord(c),x,y,inv)
    x+=12 


#-----------------------------------------------------------
@micropython.viper
def draw24x16tile(tile:int, x:int, y:int):
    # Viper pointers for quick access to the buffers
    buf = ptr16(engine_draw.back_fb_data())
    t=ptr8(tiles_big)

    pos = (y*128*16)+(x*24)+3076     # screen index
    b=tile*48  # each 24x16 tile is 24x16/8 = 48 bytes
    for py in range(0, 2):
        #print(py)
        for px in range(0,24):
	    a=t[b];
	    for px2 in range (0, 8):
	      if a & 0b1:
	         buf[pos]= 65535 
	      else:         
                 buf[pos] = 0
              a>>=1
              pos += 128
	    b +=1
	    pos-=(128*8-1)
        pos+=(128*8-24)
	
#-----------------------------------------------------------
@micropython.viper
def draw4x4tile(tile:int, x:int, y:int):
    # Viper pointers for quick access to the buffers
    buf = ptr16(engine_draw.back_fb_data())
    t=ptr8(tiles_small)

    pos = (y*128*8)+(x*8)   # screen index
    b=tile*4  # each 4x4 tile is 4 bytes
       
    for px in range(0,4):
	a=t[b];
	for px2 in range (0, 4):
	  if a & 0b1:
	     buf[pos]=65535
	     buf[pos+1]=65535
	     buf[pos+128]=65535
	     buf[pos+129]=65535 
	  else:         
             buf[pos] = 0
	     buf[pos+1] = 0
	     buf[pos+128]=0
	     buf[pos+129] = 0
          a>>=1
          pos += 256
	b +=1
	pos-=(128*8-2)

  	
#-------------------------------------------------------------
@micropython.viper
def write_maze(posn:int, value:int):
  if posn>=128 and posn<=2994:
    m=ptr8(maze)
    m[posn-128]=value

#-------------------------------------------------------------
def read_maze(posn):
  if posn<64: return(WALL_GREY)
  if posn<128: return(WALL)
  if posn>=3008: return(WALL_GREY)
  if posn>=2944: return(WALL)
  x=maze[posn-128]
  return(x)

#-------------------------------------------------------------
def seed_pseudo_random(seedval):
  seed(seedval)

#-------------------------------------------------------------
# fast pseudorandom 8-bit number generator.
# x(n+1) = ( x(n)*67+509 ) modulo 256.
# (note that this has a period of 128 instead of 256.)
def update_random():
  global random8bit
  random8bit=(random8bit*57+509)%256

#------------------------------------------------------------
def seed_random8bit():
  global random8bit
  random8bit=randint(0,255)

#-------------------------------------------------------------
# decode random8bit to a direction (1/2/3/4)
def random_direction():
  global random8bit
  update_random()  #  printf("new random=%i\n",random8bit);
  if random8bit<64: return(1)
  if random8bit<128: return(2)
  if random8bit<192: return(3)
  return(4)
  
#----------------------------------------------------
# try_left() - returns 1 if possible to move left.
def try_left(posn):
  if read_maze(posn-1)!=WALL: return(0)
  if read_maze(posn-2)!=WALL: return(0)
  if read_maze(posn+63)!=WALL: return(0)
  if read_maze(posn-65)!=WALL: return(0)
  return(1) 

#----------------------------------------------------
# try_right() - returns 1 if possible to move right.
def try_right(posn):
  if read_maze(posn+1)!=WALL: return(0)
  if read_maze(posn+2)!=WALL: return(0)
  if read_maze(posn+65)!=WALL: return(0)
  if read_maze(posn-63)!=WALL: return(0)
  return(1)

#----------------------------------------------------
# try_up() - returns 1 if possible to move up.
def try_up(posn):
  if read_maze(posn-64)!=WALL: return(0)
  if read_maze(posn-65)!=WALL: return(0)  
  if read_maze(posn-63)!=WALL: return(0)
  if read_maze(posn-128)!=WALL: return(0)
  return(1) 
  
#----------------------------------------------------
# try_down() - returns 1 if possible to move down.
def try_down(posn):
  if read_maze(posn+64)!=WALL: return(0)
  if read_maze(posn+63)!=WALL: return(0)  
  if read_maze(posn+65)!=WALL: return(0)
  if read_maze(posn+128)!=WALL: return(0)
  return(1) 


        
#-------------------------------------------------------------
#  create blank maze template...
def blank_maze():
  for i in range(0,3072):
    if i<64 or i>=3008: write_maze(i,WALL_GREY)
    else:
      if i%64==0 or i%64==63: write_maze(i,WALL_GREY)
      else: write_maze(i,WALL)
      
#--------------------------------------------------------------
# add treasure to maze....
def add_treasure(): 
  done=0
  while done==0:
    done=1
    i=(randint(0,255)%2810)+128;
    if read_maze(i)==WALL_GREY or read_maze(i-1)==WALL_GREY or read_maze(i+1)==WALL_GREY:
      done=0
  write_maze(i,TREASURE);
  return(i);

#-------------------------------------------------------------
# move treasure if distance to it is too short....
def move_treasure():
  # first, find the treasure!
  posn=HOME
  for i in range(128,128+2810):
    if read_maze(i)==TREASURE: posn=i
  write_maze(posn,CLEAR)
  print("moving treasure from",posn)
  add_treasure()
  
#-------------------------------------------------------------
#  find a random wall in maze that's good for a sword or prisoner...
def find_good_wall_spot():
  global counter2
  timer=10000
  ok=1
  while ok==1:
    timer-=1;
    if timer==0:
      print("oops timeout")
      return(0)
    counter2+=1
    if counter2>=256: counter2=0
    if counter2==173: seed_random8bit();
    update_random()
    posn=random8bit*11+128
    if read_maze(posn)==WALL: ok=0
  return(posn)

#-------------------------------------------------------------
# find a random clearing in maze that's good for a mazog...
def find_good_clear_spot():
  global counter2
  timer=10000
  ok=1
  while ok==1:
    timer-=1;
    if timer==0:
       print("oops timeout")
       return(0)
    counter2+=1
    if counter2==173: seed_random8bit()
    update_random()
    posn=random8bit*11+128
    if read_maze(posn)==CLEAR: ok=0
  return(posn)

#----------------------------------------------------
# add_pathways - generate the maze pathways.
# starts from the given treasure location.
def add_pathways(treasure_location):
  global counter
  global random8bit
  timeout=10000
  posn=treasure_location

  ok=1
  while ok==1:
    #view_map2(posn)
    #engine.tick()
    #time.sleep(0.1)
    ok=0
    d=random_direction()  # returns 1,2,3 or 4
    if d==1:
      if try_left(posn): posn-=1; write_maze(posn,CLEAR); ok=1
    if d<3 and ok==0:
      if try_right(posn): posn+=1; write_maze(posn,CLEAR); ok=1
    if d<4 and ok==0:
      if try_up(posn): posn-=64; write_maze(posn,CLEAR); ok=1    
    if ok==0:
      if try_down(posn): posn+=64; write_maze(posn,CLEAR); ok=1    
    if ok==0:
      if try_left(posn): posn-=1; write_maze(posn,CLEAR); ok=1
    if ok==0:
      if try_right(posn): posn+=1; write_maze(posn,CLEAR); ok=1
    if ok==0:
      if try_up(posn): posn-=64; write_maze(posn,CLEAR); ok=1
    #if ok==1: print("path still OK...")
    if ok==0:
     while ok==0 and timeout!=0:  # current path has ended, try to start new path
      #print("new path needed old=",posn)
      timeout-=1
      if timeout==0: # maze creation finished, find size and exit
        size=0
	for i in range(0, 3072):
	  if read_maze(i)==CLEAR: size+=1
	return(size) 
      counter=(counter+1)%256
      if counter==0: seed_random8bit();
      update_random();
      posn=random8bit*11+128; # get potential start of next path
      if read_maze(posn)==CLEAR: ok=1
      #if ok==1: print("started new path at ",posn)
      if ok==0:
        b=0
        while(b<7 and ok==0):
	  posn+=1; b+=1
	  if read_maze(posn)==CLEAR:
	    ok=1; b=10
      #if ok==1: print("started new path at ",posn)
  print("timer run out, giving up")
  size=0
  for i in range(0, 3072):
    if read_maze(i)==CLEAR: size+=1
    return(size)
      
#------------------------------------------------------------
# add the maze entrance and check it creates a valid maze.
def add_entrance():
  global posn
  
  write_maze(1279,WALL);  
  write_maze(1280,SWORD);
  write_maze(1407,WALL);
  write_maze(1408,WALL);
  
  # start location in maze saved as 1344 (HOME)...
  posn=HOME;
  ok=0
  while ok==0:
    write_maze(posn,CLEAR)
    if read_maze(posn-1)==CLEAR: ok=1   
    if ok==0 and read_maze(posn-65)==CLEAR: 
      write_maze(posn-64,CLEAR); ok=1
    if ok==0 and read_maze(posn+63)==CLEAR:
      write_maze(posn+64,CLEAR); ok=1
    posn-=1
  write_maze(posn,CLEAR)
  posn=HOME
  ok=0
  while ok==0:
    write_maze(posn,CLEAR)
    if read_maze(posn+1)==CLEAR: ok=1
    if ok==0 and read_maze(posn-63)==CLEAR:
      write_maze(posn-64,CLEAR); ok=1
    if ok==0 and read_maze(posn+65)==CLEAR:
      write_maze(posn+64,CLEAR); ok=1
    posn+=1
  write_maze(posn,CLEAR)
    

#-------------------------------------------------------------
def add_swords(swords_count):
  for i in range(0, swords_count):
    posn=find_good_wall_spot()
    if posn==0: return(0)  # give up immediately if failure
    write_maze(posn,SWORD)
  return(1)  # OK


#-------------------------------------------------------------
def add_prisoners(prisoners_count):
  for i in range(0, prisoners_count):
    posn=find_good_wall_spot()
    if posn==0: return(0)  # give up immediately if failure
    write_maze(posn,PRISONER)
  return(1)  # OK 
  
#-------------------------------------------------------------
def add_mazogs(mazogs_count):
  for i in range(0, mazogs_count):
    posn=find_good_clear_spot()
    if posn==0: return(0)  # give up immediately if failure
    write_maze(posn,MAZOG)
  return(1)  # OK 
 
#-------------------------------------------------------------
def create_maze():
  global counter2,counter
  global maze_number
  
  #seed_pseudo_random(1111); # seed RNG?

  random8bit=195; counter=1; counter2=70; # ensure consistancy  
   
  done=0
  while(done==0):
    blank_maze()
    seed_random8bit()
    treasure_location=add_treasure();
    maze_size=add_pathways(treasure_location)
    print("maze size=",maze_size)
    if maze_size>1200: done=1
    else: print("redrawing maze...")
    #view_map(HOME)
    
    if done==1: add_entrance()
    #view_map(HOME)
    seed_random8bit()
    if done==1: done=add_swords(40)
    if done==0: print("oops add_sword fail")
    if done==1: done=add_prisoners(30)
    if done==0: print("oops add_prisoner fail")
    if done==1: done=add_mazogs(38)
    if done==0: print("oops add_mazogs fail")
    # check that both left and right paths are long enough:
    write_maze(HOME-1,WALL)
    solve_maze(HOME)
    dist=get_distance()
    print("right dist=",dist)
    clear_badsearches()
    clear_trails()
    if dist==0: done=0
    write_maze(HOME-1,CLEAR)
    write_maze(HOME+1,WALL)
    solve_maze(HOME)
    dist=get_distance()
    print("left dist=",dist)
    clear_badsearches()
    clear_trails()
    if dist==0: done=0
    write_maze(HOME+1,CLEAR)

#--------------------------------------------------------------
# single frame of map view, used by view_mao()
def view_map_single(posn):
    for y in range(0,16):
      for x in range(0,16):
        tile=read_maze(posn+y*64+x-520)	
        draw4x4tile(tile,x,y)
    
#------------------------------------------------------------
# do the 16x16 map view in-game
def view_map(posn):
  global level, moves_left
  
  # charge 10 moves.... (original says 15 for level2, 
  #                      but sourcecode disagrees)
  if level>1 and moves_left>11: moves_left-=10
  
  for i in range(0,25): # forced to view map for 25 frames
    view_map_single(posn)
    draw4x4tile(MAP_STILL,8,8)
    engine.tick()
    time.sleep(0.15)
    if level==3:
      move_mazogs(posn)
      if read_maze(posn)==MAZOG: return(1) # fight!
      
#-------------------------------------------------------------
# expore map at end of a game
def explore_map():
  global posn
  while engine_io.A.is_pressed==1: engine.tick()
  while engine_io.UP.is_pressed==0 and \
        engine_io.DOWN.is_pressed==0 and \
	engine_io.LEFT.is_pressed==0 and \
	engine_io.RIGHT.is_pressed==0:
    view_map_single(posn)
    printt(0,24,"   USE D-PAD TO MOVE  ",1);
    printt(0,32," PRESS A TO SOLVE     ",1);
    printt(0,40," PRESS B FOR NEW GAME ",1);
    engine.tick()
   
  while engine_io.A.is_pressed==0:
   view_map_single(posn)
   engine.tick()
   time.sleep(0.15)
   if engine_io.RIGHT.is_pressed:  posn+=1
   if engine_io.LEFT.is_pressed: posn-=1
   if engine_io.UP.is_pressed and posn>0: posn-=64
   if engine_io.DOWN.is_pressed and posn<3000: posn+=64

#-------------------------------------------------------------
def draw_maze(posn):
  grey_screen();
  for y in range(0,5):
    for x in range(0,5):
      tile=read_maze(posn+y*64+x-130)
      if x==2 and y==2: tile=pose;
      # This does the animations....
      if frame&1 and tile==MAZOG: tile=MAZOG2
      if frame&1 and tile==TREASURE: tile=TREASURE2
      if frame&1 and tile==PRISONER: tile=PRISONER2      
      draw24x16tile(tile,x,y)  

#-------------------------------------------------------------
def clear_trails():
  for i in range(128,2944):
    tile=read_maze(i)
    if tile==TRAIL or tile==THISWAY: write_maze(i,CLEAR)
 
#-------------------------------------------------------------
def clear_badsearches():
  for i in range(128,2944):
    tile=read_maze(i)
    if tile==NOTTHISWAY: write_maze(i,CLEAR)
    if tile==NOTTHISWAY_MAZOG: write_maze(i,MAZOG)
    if tile==THISWAY_MAZOG: write_maze(i,MAZOG)
    
#-------------------------------------------------------------
# solve maze from given starting position to the treasure
def solve_maze(start):
  clear_trails()
  posn=start;
  found=0
  while found==0:
    #if posn==start or posn==start-1 or posn==start-2:
    #view_map_single(posn)
    #engine.tick()
    #time.sleep(0.1)
    tile=read_maze(posn)
    if tile==CLEAR: write_maze(posn,THISWAY)
    if tile==MAZOG: write_maze(posn,THISWAY_MAZOG)
    # check if we've found the treasure...
    if read_maze(posn+1)==TREASURE or \
    read_maze(posn-1)==TREASURE or \
    read_maze(posn+64)==TREASURE or \
    read_maze(posn-64)==TREASURE:
      found=1
    ok=0
    tile=read_maze(posn+1) # try right...
    if tile==CLEAR or tile==MAZOG: posn+=1; ok=1
    else:
      tile=read_maze(posn-1) # try left....
      if tile==CLEAR or tile==MAZOG: posn-=1; ok=1
      else:
        tile=read_maze(posn+64) # try down...
	if tile==CLEAR or tile==MAZOG: posn+=64; ok=1
	else:
	  tile=read_maze(posn-64) # try up...
	  if tile==CLEAR or tile==MAZOG: posn-=64; ok=1
    if (ok==0):  # oops! time to (continue) backtrack... 
      tile=read_maze(posn)
      if (tile==THISWAY): write_maze(posn,NOTTHISWAY)
      if (tile==THISWAY_MAZOG): write_maze(posn,NOTTHISWAY_MAZOG)
      tile=read_maze(posn+1) # try right...
      if tile==THISWAY or tile==THISWAY_MAZOG: posn+=1; ok=1
      else:
        tile=read_maze(posn-1) # try left....
        if tile==THISWAY or tile==THISWAY_MAZOG: posn-=1; ok=1
        else:
          tile=read_maze(posn+64) # try down...
 	  if tile==THISWAY or tile==THISWAY_MAZOG: posn+=64; ok=1
	  else:
	    tile=read_maze(posn-64) # try up...
	    if tile==THISWAY or tile==THISWAY_MAZOG: posn-=64; ok=1
      if ok==0:
        clear_trails(); clear_badsearches(); print("oops, solve failed"); return(0)
  
  return(1) # all OK
  
#-------------------------------------------------------------
def get_distance():
  dist=0
  for i in range(128,2944):
    tile=read_maze(i)
    if tile==THISWAY or tile==THISWAY_MAZOG: dist=dist+1
  #print("dist=",dist)
  return(dist)

#-------------------------------------------------------------
# write 'THIS WAY' files to map...
def thisway(posn):
  global frame
  clear_trails()
  if carrying==HAVE_TREASURE:
    write_maze(posn,TREASURE)
    solve_maze(HOME)
    write_maze(posn,TRAIL)
  else: solve_maze(posn)
  clear_badsearches()
  frame=50 # set countdown for thisway removal

#-------------------------------------------------------------
# fight routine. Returns 0 for player win or 'posn' if lost
def fight(posn):
  global level,moves_left,kill_moves,pose,frame,carrying
  if (level>1): moves_left+=kill_moves
  for i in range(0,5):
    for n in range(0,6):
      # avoid running down 'thisway' timer....
      if n%2==0: pose=FIGHT+(n>>1); frame=frame^1
      else: pose=MAZOG
      draw_maze(posn)
      engine.tick()
      time.sleep(0.08)
  write_maze(posn,STILL);
  if carrying==HAVE_SWORD:
     carrying=HAVE_NOTHING; 
     pose=STILL
     return(0);
  # fighting without a sword... roll D20....
  update_random()
  if (random8bit>127):
    pose=STILL
    return(0)  # phew!
  return(posn) # RIP
  
#-------------------------------------------------------------
# Process the next player move.
def check_move(posn, newposn):
  global level,moves_left,carrying,pose,frame,move_frame
  tile=read_maze(newposn)
  if tile==WALL:  # can't walk through walls...
     pose=STILL+carrying
     move_frame=0
     return(posn)
  if tile==SWORD: # grab sword, or swap with treasure.
     if carrying==HAVE_NOTHING: write_maze(newposn,WALL)
     if carrying==HAVE_TREASURE: write_maze(newposn,TREASURE)
     carrying=HAVE_SWORD
     pose=STILL+carrying
     move_frame=0
     return(posn)
  if tile==PRISONER: # get directions
     if level==3: write_maze(newposn,WALL)
     thisway(posn)
     return(posn)
  if tile==TREASURE: # grab treasure, or swap with sword
     if carrying==HAVE_NOTHING: write_maze(newposn,WALL)    
     if carrying==HAVE_SWORD: write_maze(newposn,SWORD) # swap
     carrying=HAVE_TREASURE
     pose=STILL+carrying
     move_frame=0
     return(posn)
  if tile==MAZOG:
     write_maze(posn,TRAIL)
     posn=newposn
     if fight(posn): return(posn+32768) # exit if lost
     if carrying==HAVE_SWORD: carrying=HAVE_NOTHING
  # just movement then, first check there are enough moves left   
  if level>1:
    moves_left-=1;
    if moves_left==0:  # starved
      if carrying==HAVE_TREASURE: 
         write_maze(posn,TREASURE)
	 return(65535)  # dead
  # now set pose for movement direction....
  if newposn-posn==64: pose=UP+carrying+move_frame
  if newposn-posn==-64: pose=DOWN+carrying+move_frame
  if newposn-posn==-1: pose=LEFT+carrying+move_frame
  if newposn-posn==1: pose=RIGHT+carrying+move_frame
  # leave a trail...
  write_maze(posn,TRAIL)
  move_frame=1-move_frame
  return(newposn)

#-------------------------------------------------------------
def can_move(posn):
  tile=read_maze(posn)
  if tile==CLEAR or tile==TRAIL or tile==THISWAY: return(1)
  return(0)

#-------------------------------------------------------------
def move_mazog(posn,newposn):
  write_maze(posn,CLEAR)
  write_maze(newposn,MAZOG)

#-------------------------------------------------------------
def move_mazogs(posn):
  i=128
  
  while i<2944:
    if read_maze(i)==MAZOG:
      # always pick a fight if right or left of player...
      if i==posn+1 or i==posn-1:
         move_mazog(i,posn)
         return(0) # start the fight in next frame
      dir=random_direction()
      # up... (note that mazogs don't attack face-on)
      if dir==1 and can_move(i-64) and i-64!=posn:
       move_mazog(i,i-64)
      # left.....
      if dir==3 and can_move(i-1): move_mazog(i,i-1)
  
      # now it gets tricky - avoid re-scanning some mazogs twice
  
      # right....
      if dir==4 and can_move(i+1): 
        move_mazog(i,i+1); i+=1
      # down..... (note that mazogs don't attack face-on
      if dir==2 and can_move(i+64) and i+64!=posn: 
        move_mazog(i,i+64); i+=64;
    i=i+1
  return(0) 
  
#-------------------------------------------------------------
def enter_maze():
  global frame,pose,posn,carrying
  
  while engine_io.A.is_pressed==1: engine.tick() 
  posn=HOME
  while True:
    if level==3: move_mazogs(posn)
    if read_maze(posn)==MAZOG:
      if fight(posn): return(posn) # fight result
    draw_maze(posn)
    time.sleep(0.15)
    pose=STILL+carrying
    if engine.tick():       
      if engine_io.UP.is_pressed: posn=check_move(posn,posn-64)
      if engine_io.DOWN.is_pressed: posn=check_move(posn,posn+64)
      if engine_io.LEFT.is_pressed: posn=check_move(posn,posn-1)
      if engine_io.RIGHT.is_pressed: posn=check_move(posn,posn+1)    
      if posn==65535: return(65535); # starved. 
      if posn>32768: return(posn-32768) # lost a fight!
      if engine_io.A.is_pressed: situation_report()
      if engine_io.B.is_pressed: view_map(posn)
      if frame>1:
         frame-=1
	 if frame==1: clear_trails()
      else: frame=1-frame
      
      if posn==HOME and carrying==HAVE_TREASURE: return(0); # a winner is you

#---------------------------------------------------------------
def choose_level():
  global level
  while engine_io.A.is_pressed==1: engine.tick() 
  while engine_io.A.is_pressed==0:
    black_screen()
    for y in (0,1,3,4):
       for x in range(0,5):
          draw24x16tile(WALL,x,y)
    draw24x16tile(MAZOG,2,1);
    printt(20,0," WHICH GAME ? ",0);
  
    if level==1: printt(7,58,"    TRY IT OUT     ",1);
    if level==2: printt(7,58,"  FACE A CHALLENGE ",1);
    if level==3: printt(7,58,"MANIC MOBILE MAZOGS",1);    	  
    engine.tick()
    if engine_io.UP.is_pressed==1 and level>1: level-=1; time.sleep(0.2)
    if engine_io.LEFT.is_pressed==1 and level>1: level-=1; time.sleep(0.2)
    if engine_io.DOWN.is_pressed==1 and level<3: level+=1; time.sleep(0.2)
    if engine_io.RIGHT.is_pressed==1 and level<3: level+=1; time.sleep(0.2)
         
#--------------------------------------------------------------
# spash screen for level choice
def level_splash(done):
  global level

  while engine_io.A.is_pressed==1: engine.tick()  
  black_screen()
  for y in range(0,5):
    for x in range(0,5):
      draw24x16tile(WALL,x,y)
  if level==1:
    draw24x16tile(LEFT+HAVE_TREASURE,2,1);
    printt(18,0,"  TRY IT OUT   ",0);    
  if level==2:
    draw24x16tile(RIGHT+HAVE_SWORD,2,1);
    printt(10,0," FACE A CHALLENGE ",0);
  if level==3:  
    if done==0: count=6
    else: count=0
    for i in range(1,count):
      black_screen()
      printt(1,0," MANIC MOBILE MAZOGS ",0);
      for y in range(0,5):
         for x in range(0,5):
            draw24x16tile(WALL,x,y)
      draw24x16tile(STILL,2,1);
      draw24x16tile(MAZOG2,1,1);
      draw24x16tile(MAZOG2,3,1);
      engine.tick()      
      time.sleep(0.25)
      black_screen()
      printt(1,0," MANIC MOBILE MAZOGS ",0);
      for y in range(0,5):
         for x in range(0,5):
            draw24x16tile(WALL,x,y)
      draw24x16tile(STILL,2,1);      
      draw24x16tile(MAZOG,1,1);
      draw24x16tile(MAZOG,3,1);
      engine.tick()
      time.sleep(0.25)
    black_screen()
    printt(1,0," MANIC MOBILE MAZOGS ",0);
    for y in range(0,5):
       for x in range(0,5):
          draw24x16tile(WALL,x,y)
    draw24x16tile(STILL,2,1);      
    draw24x16tile(MAZOG,1,1);
    draw24x16tile(MAZOG,3,1);    
  if done==0:
     printt(0,110," MAZE IS BEING DRAWN ",1);
  else:
     printt(0,110,"MAZE READY, PRESS 'B'",1);     
  engine.tick()

#-------------------------------------------------------------
def left_or_right():
  while engine_io.A.is_pressed==1: engine.tick()
  while engine_io.LEFT.is_pressed==0 and engine_io.RIGHT.is_pressed==0:
    view_map_single(HOME)
    printt(0,120,"  GO LEFT OR RIGHT?  ",1)
    if engine_io.B.is_pressed==1: pick_maze()
    engine.tick()
  if engine_io.LEFT.is_pressed==1: write_maze(HOME+1,WALL)
  if engine_io.RIGHT.is_pressed==1: write_maze(HOME-1,WALL)
  
  dist=0
  while dist<105:  # the game would be too easy...
    solve_maze(HOME)
    dist=get_distance()
    clear_trails(); clear_badsearches()
    print("dist to treasure=",dist)
    if dist<105: move_treasure()
  
  while engine_io.LEFT.is_pressed==1 or engine_io.RIGHT.is_pressed==1:
    engine.tick()
  while engine_io.A.is_pressed==0:
     view_map_single(HOME)
     printt(0,120,"  PRESS B FOR REPORT  ",1)
     engine.tick()

#-------------------------------------------------------------
def situation_report():
  global level,carrying,posn,initial_moves,moves_left
  
  while engine_io.A.is_pressed==1 or engine_io.B.is_pressed==1 : engine.tick()
  # charge 10 moves for this report...
  if level>1 and moves_left>11: moves_left-=10
  
  if carrying==HAVE_TREASURE:
    write_maze(posn,TREASURE)
    solve_maze(HOME)
    write_maze(posn,CLEAR)
    dist=get_distance();
  else:
    solve_maze(posn);
    dist=get_distance()
  clear_badsearches()
  clear_trails()
  done=0
  while done==0:
    grey_screen();
    printt(16,0,"SITUATION REPORT",1);
    if carrying==HAVE_TREASURE:
      printt(0,20,"MOVES BACK HOME=",1)
    else:
      printt(10,20,"MOVES TO TREASURE:",1)
    moves=" "+str(dist)+" "
    printt2(30,36,moves,1)
    if level>1:
      if moves_left==0: 
        moves_left=int(dist*4)
        initial_moves=moves_left
      printt(28,54,"MOVES LEFT:",1)  
      pl="MOVES LEFT= "
      pl=" "+str(moves_left)+" "
      printt2(30,70,pl,1)
      if carrying==HAVE_NOTHING:
        printt(20,90,"A = BUY SWORD",1)
    if level==1 or moves_left!=0:
      printt(10,112,"PRESS B FOR GAME",1)
    if level>1 and posn==HOME: # i.e. first report of game...
      printt(10,112,"PRESS B FOR MORE",1) # second report
    engine.tick()
    if engine_io.A.is_pressed==1: done=1
    # 'A' key - buy a sword? Costs half of remaining moves
    if engine_io.B .is_pressed==1 and \
    level>1 and \
    carrying==HAVE_NOTHING:
      carrying=HAVE_SWORD
      moves_left>>=1
      moves_left+=1
      done=1
  
  while engine_io.A.is_pressed==1 or engine_io.B.is_pressed==1 : engine.tick()

#-------------------------------------------------------------
def situation_report2():
  global level,initial_moves,kill_moves
  while engine_io.A.is_pressed==1 or engine_io.B.is_pressed==1 : engine.tick()
  print("level=",level)
  if level==2: kill_moves=int(initial_moves/10)
  if level==3: kill_moves=int(initial_moves*15/100)
  while engine_io.A.is_pressed==0:
    grey_screen();
    printt(16,0,"SITUATION REPORT",1);
    k="EACH KILL= +"+str(kill_moves)
    printt(0,36,k,1);
    printt(0,60,"EACH VIEW= -10 MOVES",1);
    printt(0,80,"EACH REPORT=-10 MOVES",1);
    printt(10,112,"PRESS 'B' FOR GAME",1);
    engine.tick()
  
#-------------------------------------------------------------
def starved():
  global frame
  frame=0
  for i in range(0,20):
    black_screen()
    printt(16,24,"YOU HAVE STARVED",frame);
    printt(16,40,"    TO DEATH    ",frame);
    engine.tick()
    frame=1-frame
    time.sleep(0.2)
    
#-------------------------------------------------------------
def mazogs_win(posn):
  global pose,frame
  pose=MAZOG; write_maze(posn,MAZOG)
  frame=0
  for i in range(0,20):
    draw_maze(posn)
    engine.tick()
    frame=1-frame
    time.sleep(0.1)
  black_screen(); engine.tick(); time.sleep(0.1)
  for i in range(0,20):
    draw_maze(posn)
    printt(14,112,"  DEATH TO ALL  ",frame);
    printt(14,112-16,"TREASURE SEEKERS",frame);
    engine.tick()
    frame=1-frame;
    time.sleep(0.2)

#-------------------------------------------------------------
def welcome_back():
  global posn,frame,initial_moves,moves_left
  frame=0;
  if read_maze(HOME-1)==WALL: posn=HOME+1
  else: posn=HOME-1
  write_maze(HOME-64,EXIT)
  write_maze(HOME,STILL) # reception party.
  for i in range(0,30):
    draw_maze(posn)
    printt(20,112," WELCOME BACK ",frame);
    engine.tick()
    time.sleep(0.2)
    frame=1-frame;
  while engine_io.A.is_pressed==0 and engine_io.B.is_pressed==0:
    grey_screen()
    if (level>1):
      printt(16,0,"MOVES ALLOWED:",1)
      #allowed=" "; allowed+=str(initial_moves); allowed+=" "
      allowed=" "+str(initial_moves)+" "
      printt2(32,16,allowed,1)
      printt(20,32," MOVES LEFT:",1)
      left= "MOVES LEFT="
      left=" "+str(moves_left)+" "
      printt2(32,48,left,1)
      printt(32,64," SCORE: ",1);
      score= " "+str(moves_left*100/initial_moves)+"% "
      printt2(14,80,score,1)
    printt(20,96,"A=EXAMINE MAZE",0);
    printt(20,112,"B=ANOTHER GAME",0);
    engine.tick()
  if engine_io.B.is_pressed==1: explore_map()

#-------------------------------------------------------------
def maybe_examine_maze():
  global posn
  posn=HOME
  while engine_io.A.is_pressed==0 and engine_io.B.is_pressed==0:
    grey_screen()
    printt(20,48,"A=EXAMINE MAZE",0);
    printt(20,56,"B=ANOTHER GAME",0);
    engine.tick()
    if  engine_io.B.is_pressed==1: explore_map()


#-------------------------------------------------------------
# runs the 'attract' opening screen
def title_sequence():
  while engine_io.A.is_pressed==1: engine.tick()
  frame=0
  while engine_io.A.is_pressed==0:
    grey_screen()
    
    for y in range(0,5):
      for x in range(0,5):
        draw24x16tile(WALL,x,y);
    draw24x16tile(STILL+HAVE_TREASURE,0,1);
    draw24x16tile(TRAIL,0,2);
    draw24x16tile(TRAIL,1,2);
    draw24x16tile(RIGHT+HAVE_SWORD,2,2);
    draw24x16tile(THISWAY,1,3);
    draw24x16tile(SWORD,3,3);
    printt(20,0,"  M A Z O G S  ",1) 
    printt(0,16,"A MAZE ADVENTURE GAME",1)
    printt(15,112,"PRESS B TO START",1)
    if frame==0:
      draw24x16tile(TREASURE2,1,1);
      draw24x16tile(MAZOG2,3,2);
      draw24x16tile(PRISONER,2,3);
    else:
      draw24x16tile(TREASURE,1,1);
      draw24x16tile(MAZOG,3,2);
      draw24x16tile(PRISONER2,2,3);  
    engine.tick()
    time.sleep(0.2)
    frame=1-frame

#--------------------------------------------------------------
def p10(x):
  if x==0: return(10000)
  if x==1: return(1000)
  if x==2: return(100)
  if x==3: return(10)
  if x==4: return(1)
  
#-------------------------------------------------------------
def pick_maze():
  global maze_number
  
  p=0
  while engine_io.B.is_pressed==1 or engine_io.A.is_pressed==1: engine.tick()
  while engine_io.A.is_pressed==0:
    grey_screen()
    printt(0,0,"     MAZE CHOOSER    ",1);
    printt(0,16,"PRESS B WHEN FINISHED",0);
    m=""
    if maze_number<10000: m+="0"
    if maze_number<1000: m+="0"
    if maze_number<100: m+="0"
    if maze_number<10: m+="0"
    m+=str(maze_number)
    printt(45,48,m,0)
    printt(45+p*6,32,"v",0) 
    engine.tick()
    if engine_io.LEFT.is_pressed==1 and p!=0: p-=1;
    if engine_io.RIGHT.is_pressed==1 and p!=4: p+=1;
    if engine_io.UP.is_pressed==1 and maze_number<65535-p10(p): maze_number+=p10(p)
    if engine_io.DOWN.is_pressed==1 and maze_number>p10(p): maze_number-=p10(p)
    time.sleep(0.1)
  seed_pseudo_random(maze_number); # seed RNG
  create_maze()
    
#-------------------------------------------------------------
# main game routine.
def loop_c():
  global level,posn, initial_moves, moves_left,carrying
  
  posn=HOME; moves_left=0; carrying=HAVE_NOTHING
  
  create_maze()
  
  
  title_sequence()
  choose_level()
  level_splash(0)
  create_maze()
  while engine_io.A.is_pressed==0:
    level_splash(1)
  left_or_right()
  posn=HOME
  situation_report()
  if level>1: situation_report2()
  #carrying=HAVE_TREASURE # trace
  end_posn=enter_maze()
  if end_posn==65535: starved();
  else:
    if end_posn!=0: mazogs_win(end_posn);
    else: welcome_back();
  if end_posn!=0: maybe_examine_maze();

#-------------------------------------------------------------
engine.fps_limit(60)
while 1:
  loop_c()
