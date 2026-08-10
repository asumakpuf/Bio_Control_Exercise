import math

class Tools():    
    @staticmethod
    def hex2RGB(hexColor):
        import struct
        if len(hexColor) == 7 and hexColor[0] =='#':
            return struct.unpack('BBB', bytes.fromhex(hexColor[1:]))
        else:
            return (0, 0, 0) #TODO: raise exception instead
    
    @staticmethod
    def crop(_min, _max, x, returnType=int):
        if x < _min:
            return _min
        if x > _max:
            return _max
        return returnType(x)
    
    @staticmethod
    def low(value):
        return int(int(value) & 0xff)

    @staticmethod
    def sign(value):
        if value < 0: return -1
        else: return 1
    
    @staticmethod
    def high(value):
        return int((int(value) >> 8) & 0xff)
    
    @staticmethod
    def toInt16(high, low, signed = False):
        val = low+(high<<8)
        if signed and val > 2**16/2:
            return val-2**16
        return val

    @staticmethod
    def toInt32(high, highmidt, midtlow, low, signed):
        val = low+(midtlow<<8)+(highmidt<<16)+(high<<24)
        if signed and val > 2**32/2:
            return val-2**32
        return val

    @staticmethod
    def float2bytes(In, InLow, InHigh, n):
        """Quantize float. Used on the app side for encoding float values to byte type.
        But also here for setting the direction of the eyes.

        Args:
            In(float): float to quantize, i.e. 1.2534
            InLow(float): Lowest value of float in range, e.g. -5.1237
            InHigh(float): Highest value of float in range, e.g. 7.1256
            n(int): number of bytes in output

        Returns:
            int list: int list of quantized float, e.g. [4, 174].

        """
        if In > InHigh: In = InHigh
        if In < InLow: In = InLow
        OutLow = 0
        OutHigh = 2**(8*n)-1
        inttemp = round(((In - InLow) / (InHigh - InLow)) * (OutHigh - OutLow) + OutLow)
        return list((inttemp).to_bytes(2, byteorder='big'))

    @staticmethod
    def bytes2float(In, InLow, InHigh):
        OutLow = 0
        OutHigh = 2**(8*len(In))-1
        InAsInt = int.from_bytes(In, byteorder='big')
        return (InAsInt*(InLow - InHigh) - InLow*OutHigh + InHigh*OutLow) / (OutLow - OutHigh)

    @staticmethod
    def toFiniteFloat(x):
        try: 
            x = float(x)
            if not math.isfinite(x): return False, 0
            return True, x
        except Exception as e:
            print(e)
            return False, 0
    
    @staticmethod
    def toFiniteFloats(x, y):
        resX, x = Tools.toFiniteFloat(x)
        resY, y = Tools.toFiniteFloat(y)
        return (resX and resY), x, y
        
        