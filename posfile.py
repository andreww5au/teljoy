
import os
import pickle


def ReadPosFile(Here):
    """Read the current position data and other state information
       into an correct.CalcPosition object and an sqlint.Info object.
       Return (CurrentInfo, HA, LastMod), and modify 'Here' in place.

       Used by Teljoy to read the last saved telescope position on
       startup (RA, DEC, LST) and use that as a starting position.
    """
    try:
        f = open('teljoy.pos', 'rb')
        HA, readpos, CurrentInfo = pickle.load(f)
        f.close()
    except:
        return None, 0, 0

    Here.ObjID = readpos.ObjID
    Here.Ra = readpos.Ra
    Here.Dec = readpos.Dec
    Here.Epoch = readpos.Epoch
    Here.RaC = readpos.RaC
    Here.DecC = readpos.DecC
    Here.Alt = readpos.Alt
    Here.Azi = readpos.Azi
    Here.Time.update()  # Clear time record and make it 'now' in UTC

    return CurrentInfo, HA, 0


def UpdatePosFile(Here, CurrentInfo):
    """The reverse of the above function - take a correct.CalcPosition
       object and sqlint.Info object containing position and state information,
       and write them to the database.

       Used to let external clients (Prosp, etc) access internal teljoy state
       until I replace this with an RPC call.

       Also used by Teljoy to recover the actual telescope position on startup,
       from the last saved RA, DEC, and LST.
    """

    HA = Here.RaC / 54000.0 - Here.Time.LST
    if HA < -12:
        HA += 24
    if HA > 12:
        HA -= 24

    f = open('teljoy.postmp', 'wb')
    pickle.dump((HA, Here, CurrentInfo), f)
    f.close()
    os.remove('teljoy.pos')
    os.rename('teljoy.postmp', 'teljoy.pos')
