import re

def toKB(num):
    return '{:.2f}K'.format(num/1024)

class SectionHeader:
    def __init__(self, name, addr, length, loadAddr=0):
        self.name = name
        self.addr = addr
        self.loadAddr = loadAddr
        self.length = length

    def __str__(self):
        return self.name + ' ' + hex(self.addr) + ' ' + hex(self.length) + ' ' + hex(self.loadAddr)

class MemRegion:

    PRINT_FORMAT = '| {0:<12}| {1:<15}| {2:<15}| {3:<9}| {4:<9}| {5:<9} {6:<11} {7:>7} |'

    def __init__(self, name, attr, origin, length):
        self.name = name
        self.attr = attr
        self.origin = origin
        self.length = length
        self.end = origin + length
        self.using = 0

    @staticmethod
    def factory(d: dict):
        name = d['name']
        attr = d['attr']
        origin = int(d['origin'], 16)
        length = int(d['length'], 16)
        return MemRegion(name, attr, origin, length)

    def __str__(self):
        return self.name + ' ' + self.attr + ' ' + hex(self.origin) + ' ' + hex(self.end) + ' ' + hex(self.length) + ' ' + hex(self.using)

    def printStats(self):
        if (self.length == 0):
            return MemRegion.PRINT_FORMAT.format(
                        self.name,
                        hex(self.origin), 
                        hex(self.end),
                        '0.0K',
                        '0.0K',
                        '0.0K',
                        printBar(10, 0),
                        '{:.2f}%'.format(0.0)            
            )   
        name = self.name
        origin = hex(self.origin)
        end = hex(self.end)
        length = toKB(self.length)
        free = toKB(self.length - self.using)
        using = toKB(self.using)
        bar = printBar(self.length, self.using)
        perc = '{:.2f}%'.format((self.using/self.length)*100)   
        return MemRegion.PRINT_FORMAT.format(name, origin, end, length, free, using, bar, perc)


def printBar(total, using, barlen=10):
    if total == 0:
        total = 10
    rate = (using/total)
    bar = '|'
    if (rate < 0.60):
        bar = bar + '\033[92m'
    elif (rate < 0.80):
        bar = bar + '\033[93m'
    else:
        bar = bar + '\033[91m'
    bar = bar + '{0:<'+str(barlen)+'}\033[0m|'
    return bar.format((u"\u2588" * int(round(barlen*rate,1))))

memlines = False
memNewLines = 2
maplines = False
mapNewLines = 2
readStackSize = False

mapfile = open(
    '/SURIX/KHOMP/ipac-cleanup/Ports/STM32F2XX/Output/IPAccess.map', 'r')
content = []
readNextLine = False
upstream = []
for line in mapfile:

    if (re.match(r'^Memory Configuration', line)):
        memlines = True

    if memlines:
        if (line.strip() == ''):
            memNewLines = memNewLines - 1
        if memNewLines == 0:
            memlines = False
        line = line.strip()
        line = re.sub(r'\s+', ' ', line)
        content.append(line)

    if re.match(r'^[.].*', line):
        if not ' ' in line.strip():
            readNextLine = True
        upstream.append(line.strip())
    else:
        if readNextLine:
            upstream[-1] = upstream[-1] + ' ' + line.strip()
            readNextLine = False

mapfile.close()

p = re.compile(r'^[.][a-zA-Z_-]+\s+0x[0-9a-fA-F]+\s+0x[0-9a-fA-F]+.*')
upstream = list(filter(p.search, upstream))

sections = []
lines = upstream
p = re.compile(
    r'^(?P<name>[.][a-z-A-Z0-9_-]+)\s+(?P<addr>[0-9xa-fA-F]+)+\s+(?P<length>[0-9xa-fA-F]+).*')
p2 = re.compile(
    r'^(?P<name>[.][a-z-A-Z0-9_-]+)\s+(?P<addr>[0-9xa-fA-F]+)+\s+(?P<length>[0-9xa-fA-F]+)\s+load\s+address\s+(?P<load_addr>[0-9xa-fA-F]+).*')
for l in lines:
    m = None
    loadAddr = 0
    if 'load' in l:       
        m = p2.search(l)
        loadAddr = int(m.group('load_addr'), 16)
    else:
        m = p.search(l)
    
    if m:
        name = m.group('name')
        addr = int(m.group('addr'), 16)
        length = int(m.group('length'), 16)
        sections.append(SectionHeader(name, addr, length, loadAddr))
    

# for section in sections:
#     print(section)


for line in content:
    if re.match(r'^Memory Configuration', line):
        content.remove(line)
    elif re.match(r'^Name\s+Origin\s+Length\s+Attributes', line):
        content.remove(line)
    elif re.match(r'^[*]default[*].*', line):
        content.remove(line)

regions = []
for regin in content:
    values = regin.split(' ')
    try:
        regions.append(MemRegion(
            name=values[0],
            attr=values[3],
            origin=int(values[1], 16),
            length=int(values[2], 16)
        ))
    except:
        pass


for r in regions:
    for s in sections:
        if ( s.addr >= r.origin and s.addr < r.end):
            r.using = r.using + s.length
        elif (s.name == '.data' and (s.loadAddr >= r.origin and s.loadAddr < r.end)):
            r.using = r.using + s.length


print(MemRegion.PRINT_FORMAT.format('Region', 'Start', 'End', 'Size', 'Free', 'Used', '', 'Usage(%)'))
for r in regions:
    print(r.printStats())
