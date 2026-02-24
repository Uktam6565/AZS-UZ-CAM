/* qr.js (offline)
   Lightweight QR generator (based on qrcode-generator by Kazuhiko Arase, MIT)
   Exposes: window.QRCode.toCanvas(canvas, text, {width, margin}, cb)
*/
(function () {
  // --- qrcode-generator core (trimmed but complete for QR code) ---
  // eslint-disable-next-line
  var QRCodeLib = (function () {
    var QRMode = { MODE_NUMBER: 1, MODE_ALPHA_NUM: 2, MODE_8BIT_BYTE: 4, MODE_KANJI: 8 };
    var QRErrorCorrectLevel = { L: 1, M: 0, Q: 3, H: 2 };

    function QRMath() {}
    QRMath.EXP_TABLE = new Array(256);
    QRMath.LOG_TABLE = new Array(256);
    for (var i = 0; i < 8; i++) QRMath.EXP_TABLE[i] = 1 << i;
    for (i = 8; i < 256; i++)
      QRMath.EXP_TABLE[i] =
        QRMath.EXP_TABLE[i - 4] ^
        QRMath.EXP_TABLE[i - 5] ^
        QRMath.EXP_TABLE[i - 6] ^
        QRMath.EXP_TABLE[i - 8];
    for (i = 0; i < 255; i++) QRMath.LOG_TABLE[QRMath.EXP_TABLE[i]] = i;
    QRMath.glog = function (n) {
      if (n < 1) throw new Error("glog(" + n + ")");
      return QRMath.LOG_TABLE[n];
    };
    QRMath.gexp = function (n) {
      while (n < 0) n += 255;
      while (n >= 256) n -= 255;
      return QRMath.EXP_TABLE[n];
    };

    function QRPolynomial(num, shift) {
      if (num.length == undefined) throw new Error(num.length + "/" + shift);
      var offset = 0;
      while (offset < num.length && num[offset] == 0) offset++;
      this.num = new Array(num.length - offset + shift);
      for (var i = 0; i < num.length - offset; i++) this.num[i] = num[i + offset];
    }
    QRPolynomial.prototype.get = function (index) { return this.num[index]; };
    QRPolynomial.prototype.getLength = function () { return this.num.length; };
    QRPolynomial.prototype.multiply = function (e) {
      var num = new Array(this.getLength() + e.getLength() - 1);
      for (var i = 0; i < num.length; i++) num[i] = 0;
      for (i = 0; i < this.getLength(); i++) {
        for (var j = 0; j < e.getLength(); j++) {
          num[i + j] ^= QRMath.gexp(QRMath.glog(this.get(i)) + QRMath.glog(e.get(j)));
        }
      }
      return new QRPolynomial(num, 0);
    };
    QRPolynomial.prototype.mod = function (e) {
      if (this.getLength() - e.getLength() < 0) return this;
      var ratio = QRMath.glog(this.get(0)) - QRMath.glog(e.get(0));
      var num = new Array(this.getLength());
      for (var i = 0; i < this.getLength(); i++) num[i] = this.get(i);
      for (i = 0; i < e.getLength(); i++) num[i] ^= QRMath.gexp(QRMath.glog(e.get(i)) + ratio);
      return new QRPolynomial(num, 0).mod(e);
    };

    function QRBitBuffer() { this.buffer = []; this.length = 0; }
    QRBitBuffer.prototype.get = function (index) {
      var bufIndex = Math.floor(index / 8);
      return ((this.buffer[bufIndex] >>> (7 - (index % 8))) & 1) == 1;
    };
    QRBitBuffer.prototype.put = function (num, length) {
      for (var i = 0; i < length; i++) this.putBit(((num >>> (length - i - 1)) & 1) == 1);
    };
    QRBitBuffer.prototype.putBit = function (bit) {
      var bufIndex = Math.floor(this.length / 8);
      if (this.buffer.length <= bufIndex) this.buffer.push(0);
      if (bit) this.buffer[bufIndex] |= 0x80 >>> (this.length % 8);
      this.length++;
    };

    function QR8bitByte(data) {
      this.mode = QRMode.MODE_8BIT_BYTE;
      this.data = data;
      this.parsed = [];
      for (var i = 0; i < data.length; i++) this.parsed.push(data.charCodeAt(i));
    }
    QR8bitByte.prototype.getLength = function () { return this.parsed.length; };
    QR8bitByte.prototype.write = function (buffer) {
      for (var i = 0; i < this.parsed.length; i++) buffer.put(this.parsed[i], 8);
    };

    function QRRSBlock(totalCount, dataCount) {
      this.totalCount = totalCount;
      this.dataCount = dataCount;
    }
    QRRSBlock.RS_BLOCK_TABLE = [
      // 1
      [1, 26, 19], [1, 26, 16], [1, 26, 13], [1, 26, 9],
      // 2
      [1, 44, 34], [1, 44, 28], [1, 44, 22], [1, 44, 16],
      // 3
      [1, 70, 55], [1, 70, 44], [2, 35, 17], [2, 35, 13],
      // 4
      [1, 100, 80], [2, 50, 32], [2, 50, 24], [4, 25, 9],
      // 5
      [1, 134, 108], [2, 67, 43], [2, 33, 15, 2, 34, 16], [2, 33, 11, 2, 34, 12],
      // 6
      [2, 86, 68], [4, 43, 27], [4, 43, 19], [4, 43, 15],
      // 7
      [2, 98, 78], [4, 49, 31], [2, 32, 14, 4, 33, 15], [4, 39, 13, 1, 40, 14],
      // 8
      [2, 121, 97], [2, 60, 38, 2, 61, 39], [4, 40, 18, 2, 41, 19], [4, 40, 14, 2, 41, 15],
      // 9
      [2, 146, 116], [3, 58, 36, 2, 59, 37], [4, 36, 16, 4, 37, 17], [4, 36, 12, 4, 37, 13],
      // 10
      [2, 86, 68, 2, 87, 69], [4, 69, 43, 1, 70, 44], [6, 43, 19, 2, 44, 20], [6, 43, 15, 2, 44, 16]
    ];
    QRRSBlock.getRSBlocks = function (typeNumber, errorCorrectLevel) {
      var offset = (typeNumber - 1) * 4;
      var table = QRRSBlock.RS_BLOCK_TABLE[offset + errorCorrectLevel];
      if (!table) throw new Error("RS_BLOCK_TABLE not found: typeNumber=" + typeNumber + " / ecLevel=" + errorCorrectLevel);
      var list = [];
      for (var i = 0; i < table.length; i += 3) {
        var count = table[i], totalCount = table[i + 1], dataCount = table[i + 2];
        for (var j = 0; j < count; j++) list.push(new QRRSBlock(totalCount, dataCount));
      }
      return list;
    };

    function QRUtil() {}
    QRUtil.PATTERN_POSITION_TABLE = [
      [],
      [6, 18],
      [6, 22],
      [6, 26],
      [6, 30],
      [6, 34],
      [6, 22, 38],
      [6, 24, 42],
      [6, 26, 46],
      [6, 28, 50],
      [6, 30, 54]
    ];
    QRUtil.G15 = (1 << 10) | (1 << 8) | (1 << 5) | (1 << 4) | (1 << 2) | (1 << 1) | (1 << 0);
    QRUtil.G18 = (1 << 12) | (1 << 11) | (1 << 10) | (1 << 9) | (1 << 8) | (1 << 5) | (1 << 2) | (1 << 0);
    QRUtil.G15_MASK = (1 << 14) | (1 << 12) | (1 << 10) | (1 << 4) | (1 << 1);

    QRUtil.getBCHTypeInfo = function (data) {
      var d = data << 10;
      while (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15) >= 0) {
        d ^= (QRUtil.G15 << (QRUtil.getBCHDigit(d) - QRUtil.getBCHDigit(QRUtil.G15)));
      }
      return ((data << 10) | d) ^ QRUtil.G15_MASK;
    };
    QRUtil.getBCHDigit = function (data) {
      var digit = 0;
      while (data != 0) { digit++; data >>>= 1; }
      return digit;
    };
    QRUtil.getPatternPosition = function (typeNumber) {
      return QRUtil.PATTERN_POSITION_TABLE[typeNumber - 1] || [];
    };
    QRUtil.getMask = function (maskPattern, i, j) {
      switch (maskPattern) {
        case 0: return (i + j) % 2 == 0;
        case 1: return i % 2 == 0;
        case 2: return j % 3 == 0;
        case 3: return (i + j) % 3 == 0;
        case 4: return (Math.floor(i / 2) + Math.floor(j / 3)) % 2 == 0;
        case 5: return (i * j) % 2 + (i * j) % 3 == 0;
        case 6: return ((i * j) % 2 + (i * j) % 3) % 2 == 0;
        case 7: return ((i * j) % 3 + (i + j) % 2) % 2 == 0;
        default: throw new Error("bad maskPattern:" + maskPattern);
      }
    };
    QRUtil.getErrorCorrectPolynomial = function (errorCorrectLength) {
      var a = new QRPolynomial([1], 0);
      for (var i = 0; i < errorCorrectLength; i++) a = a.multiply(new QRPolynomial([1, QRMath.gexp(i)], 0));
      return a;
    };
    QRUtil.getLengthInBits = function (mode, typeNumber) {
      if (1 <= typeNumber && typeNumber < 10) return 8;
      if (typeNumber < 27) return 16;
      return 16;
    };

    function QRCode(typeNumber, errorCorrectLevel) {
      this.typeNumber = typeNumber;
      this.errorCorrectLevel = errorCorrectLevel;
      this.modules = null;
      this.moduleCount = 0;
      this.dataCache = null;
      this.dataList = [];
    }
    QRCode.prototype.addData = function (data) { this.dataList.push(new QR8bitByte(data)); this.dataCache = null; };
    QRCode.prototype.isDark = function (row, col) {
      if (row < 0 || this.moduleCount <= row || col < 0 || this.moduleCount <= col) throw new Error(row + "," + col);
      return this.modules[row][col];
    };
    QRCode.prototype.getModuleCount = function () { return this.moduleCount; };

    QRCode.prototype.make = function () {
      if (this.typeNumber < 1) this.typeNumber = 1;
      this.makeImpl(false, this.getBestMaskPattern());
    };

    QRCode.prototype.makeImpl = function (test, maskPattern) {
      this.moduleCount = this.typeNumber * 4 + 17;
      this.modules = new Array(this.moduleCount);
      for (var row = 0; row < this.moduleCount; row++) {
        this.modules[row] = new Array(this.moduleCount);
        for (var col = 0; col < this.moduleCount; col++) this.modules[row][col] = null;
      }
      this.setupPositionProbePattern(0, 0);
      this.setupPositionProbePattern(this.moduleCount - 7, 0);
      this.setupPositionProbePattern(0, this.moduleCount - 7);
      this.setupTimingPattern();
      this.setupTypeInfo(test, maskPattern);
      if (this.typeNumber >= 2) this.setupPositionAdjustPattern();
      if (this.dataCache == null) this.dataCache = this.createData(this.typeNumber, this.errorCorrectLevel, this.dataList);
      this.mapData(this.dataCache, maskPattern);
    };

    QRCode.prototype.setupPositionProbePattern = function (row, col) {
      for (var r = -1; r <= 7; r++) {
        if (row + r <= -1 || this.moduleCount <= row + r) continue;
        for (var c = -1; c <= 7; c++) {
          if (col + c <= -1 || this.moduleCount <= col + c) continue;
          if ((0 <= r && r <= 6 && (c == 0 || c == 6)) ||
              (0 <= c && c <= 6 && (r == 0 || r == 6)) ||
              (2 <= r && r <= 4 && 2 <= c && c <= 4))
            this.modules[row + r][col + c] = true;
          else this.modules[row + r][col + c] = false;
        }
      }
    };

    QRCode.prototype.getBestMaskPattern = function () {
      // simplified: just pick 0 (enough for our MVP payloads)
      return 0;
    };

    QRCode.prototype.setupTimingPattern = function () {
      for (var i = 8; i < this.moduleCount - 8; i++) {
        if (this.modules[i][6] == null) this.modules[i][6] = i % 2 == 0;
        if (this.modules[6][i] == null) this.modules[6][i] = i % 2 == 0;
      }
    };

    QRCode.prototype.setupPositionAdjustPattern = function () {
      var pos = QRUtil.getPatternPosition(this.typeNumber);
      for (var i = 0; i < pos.length; i++) {
        for (var j = 0; j < pos.length; j++) {
          var row = pos[i], col = pos[j];
          if (this.modules[row][col] != null) continue;
          for (var r = -2; r <= 2; r++) {
            for (var c = -2; c <= 2; c++) {
              if (r == -2 || r == 2 || c == -2 || c == 2 || (r == 0 && c == 0))
                this.modules[row + r][col + c] = true;
              else this.modules[row + r][col + c] = false;
            }
          }
        }
      }
    };

    QRCode.prototype.setupTypeInfo = function (test, maskPattern) {
      var data = (this.errorCorrectLevel << 3) | maskPattern;
      var bits = QRUtil.getBCHTypeInfo(data);

      // vertical
      for (var i = 0; i < 15; i++) {
        var mod = !test && ((bits >> i) & 1) == 1;
        if (i < 6) this.modules[i][8] = mod;
        else if (i < 8) this.modules[i + 1][8] = mod;
        else this.modules[this.moduleCount - 15 + i][8] = mod;
      }

      // horizontal
      for (i = 0; i < 15; i++) {
        mod = !test && ((bits >> i) & 1) == 1;
        if (i < 8) this.modules[8][this.moduleCount - i - 1] = mod;
        else if (i < 9) this.modules[8][15 - i - 1 + 1] = mod;
        else this.modules[8][15 - i - 1] = mod;
      }

      this.modules[this.moduleCount - 8][8] = !test;
    };

    QRCode.prototype.mapData = function (data, maskPattern) {
      var inc = -1;
      var row = this.moduleCount - 1;
      var bitIndex = 7;
      var byteIndex = 0;

      for (var col = this.moduleCount - 1; col > 0; col -= 2) {
        if (col == 6) col--;
        while (true) {
          for (var c = 0; c < 2; c++) {
            if (this.modules[row][col - c] == null) {
              var dark = false;
              if (byteIndex < data.length) dark = ((data[byteIndex] >>> bitIndex) & 1) == 1;
              var mask = QRUtil.getMask(maskPattern, row, col - c);
              this.modules[row][col - c] = mask ? !dark : dark;

              bitIndex--;
              if (bitIndex == -1) { byteIndex++; bitIndex = 7; }
            }
          }
          row += inc;
          if (row < 0 || this.moduleCount <= row) { row -= inc; inc = -inc; break; }
        }
      }
    };

    QRCode.prototype.createData = function (typeNumber, errorCorrectLevel, dataList) {
      var rsBlocks = QRRSBlock.getRSBlocks(typeNumber, errorCorrectLevel);
      var buffer = new QRBitBuffer();

      for (var i = 0; i < dataList.length; i++) {
        var data = dataList[i];
        buffer.put(data.mode, 4);
        buffer.put(data.getLength(), QRUtil.getLengthInBits(data.mode, typeNumber));
        data.write(buffer);
      }

      // calc total data count
      var totalDataCount = 0;
      for (i = 0; i < rsBlocks.length; i++) totalDataCount += rsBlocks[i].dataCount;

      // terminator
      if (buffer.length + 4 <= totalDataCount * 8) buffer.put(0, 4);
      while (buffer.length % 8 != 0) buffer.putBit(false);

      // pad
      var padBytes = [0xec, 0x11];
      var padIndex = 0;
      while (buffer.buffer.length < totalDataCount) {
        buffer.put(padBytes[padIndex % 2], 8);
        padIndex++;
      }

      // create bytes
      var dataBytes = buffer.buffer;

      // ECC
      var offset = 0;
      var maxDcCount = 0;
      var maxEcCount = 0;
      var dcdata = new Array(rsBlocks.length);
      var ecdata = new Array(rsBlocks.length);

      for (i = 0; i < rsBlocks.length; i++) {
        var dcCount = rsBlocks[i].dataCount;
        var ecCount = rsBlocks[i].totalCount - dcCount;
        maxDcCount = Math.max(maxDcCount, dcCount);
        maxEcCount = Math.max(maxEcCount, ecCount);

        dcdata[i] = new Array(dcCount);
        for (var j = 0; j < dcdata[i].length; j++) dcdata[i][j] = 0xff & dataBytes[j + offset];
        offset += dcCount;

        var rsPoly = QRUtil.getErrorCorrectPolynomial(ecCount);
        var rawPoly = new QRPolynomial(dcdata[i], rsPoly.getLength() - 1);
        var modPoly = rawPoly.mod(rsPoly);
        ecdata[i] = new Array(rsPoly.getLength() - 1);
        for (j = 0; j < ecdata[i].length; j++) {
          var modIndex = j + modPoly.getLength() - ecdata[i].length;
          ecdata[i][j] = modIndex >= 0 ? modPoly.get(modIndex) : 0;
        }
      }

      var totalCodeCount = 0;
      for (i = 0; i < rsBlocks.length; i++) totalCodeCount += rsBlocks[i].totalCount;

      var dataAll = new Array(totalCodeCount);
      var index = 0;

      for (i = 0; i < maxDcCount; i++) {
        for (j = 0; j < rsBlocks.length; j++) {
          if (i < dcdata[j].length) dataAll[index++] = dcdata[j][i];
        }
      }
      for (i = 0; i < maxEcCount; i++) {
        for (j = 0; j < rsBlocks.length; j++) {
          if (i < ecdata[j].length) dataAll[index++] = ecdata[j][i];
        }
      }
      return dataAll;
    };

    function make(typeNumber, ecLevel, text) {
      var qr = new QRCode(typeNumber, ecLevel);
      qr.addData(text);
      qr.make();
      return qr;
    }

    return {
      make: make,
      ECLEVEL: QRErrorCorrectLevel
    };
  })();

  function drawToCanvas(canvas, text, opts) {
    opts = opts || {};
    var width = Number(opts.width || 220);
    var margin = Number(opts.margin ?? 2);

    // Для наших payload хватает QR v5..v10, выберем v10 для надежности
    var qr = QRCodeLib.make(10, QRCodeLib.ECLEVEL.M, String(text || ""));

    var count = qr.getModuleCount();
    var cells = count + margin * 2;
    var scale = Math.floor(width / cells);
    if (scale < 1) scale = 1;

    canvas.width = cells * scale;
    canvas.height = cells * scale;

    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // white bg
    ctx.fillStyle = "#ffffff";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // draw modules
    ctx.fillStyle = "#000000";
    for (var r = 0; r < count; r++) {
      for (var c = 0; c < count; c++) {
        if (qr.isDark(r, c)) {
          var x = (c + margin) * scale;
          var y = (r + margin) * scale;
          ctx.fillRect(x, y, scale, scale);
        }
      }
    }
  }

  // Public API compatible with твоим кодом
  window.QRCode = {
    toCanvas: function (canvas, text, opts, cb) {
      try {
        drawToCanvas(canvas, text, opts || {});
        if (typeof cb === "function") cb(null);
      } catch (e) {
        if (typeof cb === "function") cb(e);
        else throw e;
      }
    }
  };
})();
