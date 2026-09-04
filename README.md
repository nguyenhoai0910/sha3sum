# Hướng Dẫn Kiểm Tra Hash File (SHA256 / SHA3 / BLAKE2)

## 1. Hàm PowerShell cơ bản: `SHA256`

Hàm gốc tính SHA256, có thêm tùy chọn so sánh với chuỗi hash cho trước.

```powershell
function SHA256 {
    <#
    .SYNOPSIS
    Get the file's SHA256 checksum, optionally comparing it to a given hash string
    #>
    param(
        [Parameter(Mandatory=$true)]
        [string]$File = (Get-ChildItem -File),

        [Parameter(Mandatory=$false)]
        [string]$CompareHash
    )
    
    if (-not (Test-Path -Path $File -PathType Leaf)) {
        Write-Error "File not found or is a directory: '$File'"
        return
    }

    try {
        $computedHash = (Get-FileHash -Path $File -Algorithm SHA256).Hash

        if ($PSBoundParameters.ContainsKey('CompareHash')) {
            if ($computedHash -eq $CompareHash.Trim()) {
                Write-Host "[SHA256] MATCH: Hashes are identical." -ForegroundColor Green
            }
            else {
                Write-Host "[SHA256] NO MATCH: Hashes are different." -ForegroundColor Red
            }
            Write-Host "Computed : $computedHash"
            Write-Host "Provided : $($CompareHash.Trim())"
        }
        else {
            $computedHash
        }
    }
    catch {
        Write-Error "An error occurred while calculating the hash: $($_.Exception.Message)"
    }
}
```

**Cách dùng:**
```powershell
SHA256 -File "C:\path\to\file.iso" -CompareHash "3a7bd3e2360a3d..."
```

> Lưu ý: `-eq` trong PowerShell so sánh chuỗi không phân biệt hoa/thường, và dùng `.Trim()` để loại bỏ khoảng trắng thừa khi copy-paste hash.

---

## 2. Các thuật toán hash `Get-FileHash` hỗ trợ sẵn

| Algorithm | Độ dài | Ghi chú |
|---|---|---|
| MD5 | 128-bit | Nhanh, không an toàn cho bảo mật, chỉ dùng check lỗi truyền file |
| SHA1 | 160-bit | Cũ, dùng nhiều trong Git |
| **SHA256** | 256-bit | **Phổ biến nhất**, mặc định của `Get-FileHash` |
| SHA384 | 384-bit | Ít dùng |
| SHA512 | 512-bit | An toàn cao, cho file lớn/quan trọng |
| RIPEMD160 | 160-bit | Chỉ có ở Windows PowerShell 5.1, đã bỏ ở PS7+ |

Kiểm tra danh sách chính xác trên máy bạn:
```powershell
(Get-Command Get-FileHash).Parameters['Algorithm'].Attributes.ValidValues
```

### Với video dài (file lớn)
- Cần **an toàn cao / verify từ nguồn ngoài**: dùng **SHA256** (chuẩn phổ biến, dễ đối chiếu với hash nhà phát hành công bố).
- Cần **tốc độ tối đa**, chỉ để check lỗi copy/tải: **MD5** hoặc **SHA1** cũng đủ dùng.
- Tốc độ hash với file rất lớn phụ thuộc chủ yếu vào **tốc độ đọc ổ đĩa (I/O)**, không phải CPU — chênh lệch giữa các thuật toán thường không quá lớn trên SSD.

Benchmark thử trên máy bạn:
```powershell
$file = "D:\path\to\video.mp4"
Measure-Command { Get-FileHash -Path $file -Algorithm MD5 }
Measure-Command { Get-FileHash -Path $file -Algorithm SHA256 }
Measure-Command { Get-FileHash -Path $file -Algorithm SHA1 }
```

---

## 3. Các thuật toán mạnh hơn SHA512 (không có sẵn trong `Get-FileHash`)

| Thuật toán | Độ dài | Ghi chú |
|---|---|---|
| SHA3-256 / SHA3-512 | 256/512-bit | Thế hệ mới của SHA-2, thiết kế Keccak |
| BLAKE2b | tối đa 512-bit | Nhanh hơn SHA256/SHA512 nhiều, an toàn tương đương/hơn |
| BLAKE3 | 256-bit (mở rộng được) | Cực nhanh, tận dụng đa luồng, cần cài công cụ ngoài (`b3sum`) |
| CRC32/CRC64 | 32/64-bit | Không phải hash bảo mật, chỉ check lỗi nhanh |

`Get-FileHash` không hỗ trợ các thuật toán này → cần dùng Python (`hashlib` có sẵn SHA3 và BLAKE2, không cần cài `pip` thêm).

---

## 4. Script Python: `sha3sum.py`

Hỗ trợ SHA3-256, SHA3-512, BLAKE2b, BLAKE2s — có màu xanh/đỏ khi so sánh hash (dùng `colorama` để tương thích tốt trên mọi terminal Windows).

Cài thư viện màu trước (chỉ cần 1 lần):
```powershell
pip install colorama
```

```python
#!/usr/bin/env python3
import hashlib
import sys
import argparse
from colorama import init, Fore
init(autoreset=True)

def hash_file(file_path, algo, chunk_size=65536):
    h = hashlib.new(algo)
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()

def main():
    parser = argparse.ArgumentParser(description="Compute SHA3/BLAKE2 hash of a file")
    parser.add_argument("file", help="Path to file")
    parser.add_argument("-a", "--algo", default="sha3_256",
                         choices=["sha3_256", "sha3_512", "blake2b", "blake2s"],
                         help="Hash algorithm (default: sha3_256)")
    parser.add_argument("-c", "--compare", help="Hash string to compare against")
    args = parser.parse_args()

    computed = hash_file(args.file, args.algo)

    if args.compare:
        match = computed.lower() == args.compare.strip().lower()
        print(f"Computed: {computed}")
        print(f"Provided: {args.compare.strip()}")
        status = "MATCH" if match else "NO MATCH"
        detail = "identical" if match else "different"
        color = Fore.GREEN if match else Fore.RED
        print(f"{color}[{args.algo.upper()}] {status}: Hashes are {detail}.")
        sys.exit(0 if match else 1)
    else:
        print(computed)

if __name__ == "__main__":
    main()
```

> Lưu ý quan trọng: script đọc file theo từng **chunk** (`f.read(chunk_size)`) thay vì đọc cả file vào RAM (`f.read()`), tránh tràn bộ nhớ với video dung lượng lớn.

**Cách dùng:**
```powershell
python sha3sum.py "D:\video.mp4" -a sha3_256
python sha3sum.py "D:\video.mp4" -a sha3_512 -c "3a7bd3e2360a3d..."
```

Kiểm tra các thuật toán hash mà `hashlib` hỗ trợ sẵn trên máy:
```python
import hashlib
print(hashlib.algorithms_available)
```

---

## 5. Hàm PowerShell wrapper gọi script Python: `SHA3`

```powershell
function SHA3 {
    param(
        [Parameter(Mandatory=$true)]
        [string]$File,

        [ValidateSet("sha3_256", "sha3_512", "blake2b", "blake2s")]
        [string]$Algorithm = "sha3_256",

        [string]$CompareHash
    )

    if (-not (Test-Path -Path $File -PathType Leaf)) {
        Write-Error "File not found: '$File'"
        return
    }

    $scriptPath = "C:\Scripts\sha3sum.py"  # sửa đường dẫn cho đúng máy bạn

    if ($CompareHash) {
        python $scriptPath $File -a $Algorithm -c $CompareHash
    }
    else {
        python $scriptPath $File -a $Algorithm
    }
}
```

**Cách dùng:**
```powershell
SHA3 -File "D:\video.mp4"
SHA3 -File "D:\video.mp4" -Algorithm sha3_512
SHA3 -File "D:\video.mp4" -Algorithm blake2b -CompareHash "abc123..."
```

---

## 6. Đóng gói thành file `.exe` (tùy chọn, để gọi lệnh trực tiếp như `yt-dlp`)

### Cài PyInstaller
```powershell
pip install pyinstaller
```

### Kiểm tra đã cài chưa
```powershell
pip show pyinstaller
```

### Build file .exe
Nếu `pyinstaller` không được nhận diện trực tiếp (do PATH chưa trỏ tới thư mục `Scripts`), dùng cách chắc ăn:

```powershell
python -m PyInstaller --onefile --hidden-import colorama sha3sum.py
```

File `.exe` sẽ nằm trong thư mục `dist\`. Copy vào thư mục có trong `PATH` để gọi lệnh trực tiếp:
```powershell
sha3sum.exe -a sha3_256 "D:\video.mp4"
```

### Thêm PATH vĩnh viễn (nếu muốn gọi `pyinstaller` trực tiếp sau này)
```powershell
[Environment]::SetEnvironmentVariable(
    "Path",
    $env:Path + ";C:\Python314\Scripts",
    "User"
)
```
> Sửa `C:\Python314\Scripts` theo đường dẫn cài Python thực tế trên máy bạn (kiểm tra bằng `pip show pyinstaller`, xem dòng `Location`).

Sau khi chạy, **đóng và mở lại PowerShell**, kiểm tra:
```powershell
pyinstaller --version
```

### Lỗi thường gặp: `.exe` báo `ModuleNotFoundError: No module named 'colorama'`

```
Traceback (most recent call last):
  File "sha3sum.py", line 5, in <module>
    from colorama import init, Fore
ModuleNotFoundError: No module named 'colorama'
[PYI-2140:ERROR] Failed to execute script 'sha3sum' due to unhandled exception!
```

**Nguyên nhân:** PyInstaller **không tự cài package thiếu lúc chạy** — nó chỉ đóng gói sẵn những thư viện có trên máy tại **thời điểm build**. Nếu `colorama` chưa được cài vào đúng Python dùng để build, hoặc PyInstaller không detect được import, `.exe` sẽ thiếu module này.

**Cách sửa:**

1. Đảm bảo `colorama` đã cài đúng vào Python dùng để build:
```powershell
python -m pip install colorama
python -m pip show colorama
```

2. Xóa build cũ và build lại, chỉ định rõ `--hidden-import`:
```powershell
Remove-Item -Recurse -Force build, dist, sha3sum.spec -ErrorAction SilentlyContinue
python -m PyInstaller --onefile --clean --hidden-import colorama sha3sum.py
```

3. Chạy lại thử:
```powershell
.\dist\sha3sum.exe -a sha3_256 "D:\video.mp4"
```

4. Nếu vẫn lỗi, kiểm tra xem có nhiều bản Python trên máy gây lệch môi trường build không:
```powershell
python -c "import colorama; print(colorama.__file__)"
```
Nếu lệnh trên chạy được nhưng build `.exe` vẫn báo thiếu `colorama`, dùng cờ `--clean` để PyInstaller quét lại từ đầu (đã có trong lệnh build ở bước 2).

---

## 7. Ghi chú thêm

- **Lỗi font tiếng Việt trong PowerShell:** do encoding console mặc định không phải UTF-8. Có thể khắc phục bằng `chcp 65001` hoặc dùng Windows Terminal / PowerShell 7 thay vì console cũ.
- **Màu trong Python:** `print()` mặc định không có màu. Dùng ANSI escape codes trực tiếp (`\033[92m` xanh, `\033[91m` đỏ, `\033[0m` reset) hoặc thư viện `colorama` (khuyên dùng vì tương thích tốt hơn trên các phiên bản Windows console cũ).

## 8. Windows SmartScreen Warning

File chưa được ký certificate do chi phí cao.
Nếu bị cảnh báo: Click "More info" → "Run anyway"

Bạn có thể tự build từ source:
    pip install pyinstaller colorama
    python -m PyInstaller --onefile sha3sum.py
