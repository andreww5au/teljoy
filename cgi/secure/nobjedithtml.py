
"""HTML templates for the 'nobjedit.py' script, used by nobjedit and parsed by htmlutil.py
   Inside each string, names of the form ##variable## are substituted with the value of the specified 
   variable in a dictionary, passed to the 'subdict' function.
"""


header="""

<html>
<head>
<title>New/Edit object ##ObjID## </title>
</head>
<body bgcolor="#ffffff">
<h1 align="center">New/Edit object ##ObjID## </h1>

<form action="/cgi-bin/secure/nobjedit" METHOD="POST">

"""


savedmessage="""
<P>Go to <A href="../al/aobjlist">Objects Database</A>, or <P>\n
       <A href="../platstat">Observing Status Page</A>.<P>
"""


confirmobject="""
Are you sure you wish to save the event below? Use the 'back' button on your browser
if the details below are not correct<p>

<table border=1>
  <tr>
    <td><input type="hidden" name="ObjID" value="##ObjID##"> ObjID: </td>
    <td>##ObjID##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="name" value="##name##"> name: </td>
    <td>##name##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="ObjRA" value="##ObjRA##"> ObjRA: </td>
    <td>##ObjRA##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="ObjDec" value="##ObjDec##"> ObjDec: </td>
    <td>##ObjDec##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="ObjEpoch" value="##ObjEpoch##"> ObjEpoch: </td>
    <td>##ObjEpoch##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="filtnames" value="##filtnames##"> Filt Names: </td>
    <td>##filtnames##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="exptimes" value="##exptimes##"> Exptimes: </td>
    <td>##exptimes##</td>
  </tr>
  <tr>
    <td>XYpos: </td>
    <td><input type="text" name="XYpos_X" value="##XYpos_X##">, &nbsp;
        <input type="text" name="XYpos_Y" value="##XYpos_Y##"></td>
  </tr>
  <tr>
    <td><input type="hidden" name="type" value="##type##"> Type: </td>
    <td>##type##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="period" value="##period##"> Obs Interval: </td>
    <td>##period##</td>
  </tr>
  <tr>
    <td><input type="hidden" name="comment" value="##comment##"> Comment: </td>
    <td>##comment##</td>
  </tr>


</table><p>
<input type="submit" name="Yes" value="Yes">
<input type="submit" name="No" value="No">

"""



newobject="""

Enter event parameters:<p>

<table border=1>
  <tr>
    <td>ObjID</td>
    <td><input type="text" name="ObjID" value="##ObjID##"></td>
    <td>Eg, EB2K005</td>
  </tr>
  <tr>
    <td>name</td>
    <td><input type="text" name="name" value="##name##"></td>
    <td>Eg, EB-2K-005</td>
  </tr>
  <tr>
    <td>ObjRA</td>
    <td><input type="text" name="ObjRA" value="##ObjRA##"></td>
    <td>Eg, 18:05:23.45</td>
  </tr>
  <tr>
    <td>ObjDec</td>
    <td><input type="text" name="ObjDec" value="##ObjDec##"></td>
    <td>Eg, -32:23:24</td>
  </tr>
  <tr>
    <td>ObjEpoch</td>
    <td><input type="text" name="ObjEpoch" value="##ObjEpoch##"></td>
    <td>Eg, 2000.0</td>
  </tr>
  <tr>
    <td>FiltNames</td>
    <td><input type="text" name="filtnames" value="##filtnames##"></td>
    <td>Eg, I or I,V,R</td>
  </tr>
  <tr>
    <td>Exptimes</td>
    <td><input type="text" name="exptimes" value="##exptimes##"></td>
    <td>in seconds, Eg, 600 or 10,30,20</td>
  </tr>
  <tr>
    <td>type</td>
    <td><input type="text" name="type" value="##type##"></td>
    <td>Eg, PLANET</td>
  </tr>
  <tr>
    <td>period</td>
    <td><input type="text" name="period" value="##period##"></td>
    <td>in days, eg 0.25</td>
  </tr>
  <tr>
    <td>comment</td>
    <td><input type="text" name="comment" value="##comment##"></td>
    <td>Eg, very faint at baseline</td>
  </tr>
</table><p>

<input type="submit" name="save" value="Save changes">

"""

gstarheader = """
<table border=1>
<tr>
  <th>Num</th>
  <th>RA</th>
  <th>Dec</th>
  <th>Mag</th>
  <th>X</th>
  <th>Y</th>
</tr>
"""

gstartrailer = """
</table>

<p>
Best guide star candidate shown below in red.
</p>

"""



trailer="""

</form>
</body>
</html>

"""
