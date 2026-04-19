# massDNSScanner

<div align="center">

**Advanced DNS Server Discovery & Enumeration Tool**

*Based on an original idea by **Amir*** ✨

Automate masscan scanning, VPN client automation, and DNS server analysis in one powerful workflow.

</div>

---

## 📋 Table of Contents
- [Overview](#-overview)
- [Features](#-features)
- [How It Works](#-how-it-works)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
  - [Basic Usage](#basic-usage)
  - [Command Line Options](#command-line-options)
  - [Usage Examples](#usage-examples)
- [Workflow](#-workflow)
- [Output Files](#-output-files)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🔭 Overview

**massDNSScanner** is a comprehensive automation tool to discover and enumerate DNS servers across large IP ranges. It seamlessly integrates:

1. **Masscan** - High-speed port scanning for DNS servers (port 53)
2. **VPN Client Automation** - Automated interaction with MasterDnsVPN client for DNS query collection
3. **DNS Analysis** - Statistical analysis to identify the most frequently used DNS resolvers

> 💡 **Credits**: This project is based on an original idea and concept by **Amir**. The implementation extends his vision into a production-ready automation tool.


---

## ✨ Features

### Core Capabilities
- 🚀 **High-Speed Scanning**: Leverages masscan for scanning up to 10,000 packets/second
- 🔍 **Automatic Gateway Discovery**: Intelligently detects router MAC address for optimal scanning
- 🤖 **VPN Client Automation**: Automates multiple rounds of VPN client execution
- 📊 **Smart Analysis**: Extracts and ranks DNS servers by frequency across all rounds
- 🎯 **Flexible Workflow**: Run complete scan, skip masscan, or analyze existing results
- **Multiple Output Formats**: Raw masscan output, clean IP lists, and detailed analysis reports
- **Robust Error Handling**: Handles encoding issues and gracefully manages process interruptions
- **Interactive & CLI Modes**: Use interactively or integrate into automated scripts
- **Detailed Statistics**: Shows occurrence frequency, percentage, and file distribution
- **Resume Capability**: Skip scanning and analyze existing results

### Technical Highlights
- Binary-safe output processing for reliable VPN client monitoring
- Alternative byte-by-byte reading mode for encoding-challenged environments
- Comprehensive signal handling (Ctrl+C support)
- UTF-8 encoding with fallback options for Windows consoles

---

### Detailed Process Flow

1. **Gateway Discovery** (Optional)
   - Queries ARP table to find default gateway MAC
   - Falls back to route-based detection if needed
   - Essential for optimal masscan performance on local networks

2. **Masscan Execution**
   - Scans specified IP range for open port 53 (DNS)
   - Uses router MAC for efficient local network scanning
   - Outputs in list format (`-oL`) for easy parsing

3. **VPN Client Automation**
   - Executes MasterDnsVPN client for specified number of rounds
   - Monitors output for "Session init attempt" trigger phrase
   - Automatically terminates after trigger detection
   - Each round generates DNS query logs in `tmp/` folder

4. **Result Analysis**
   - Parses all result files in `tmp/` folder
   - Extracts DNS server IPs using intelligent pattern matching
   - Calculates frequency statistics and rankings
   - Generates comprehensive reports

---

## 📦 Prerequisites

### Required Software
| Component | Purpose | Download |
|-----------|---------|----------|
| **Python 3.7+** | Core runtime | [python.org](https://python.org) |
| **Npcap 1.87** | Packet capture library (REQUIRED for masscan) | [npcap.com](https://npcap.com/#download) |
| **Masscan** | Port scanning | [GitHub - robertdavidgraham/masscan](https://github.com/robertdavidgraham/masscan) |
| **MasterDnsVPN Client** | DNS query generation | [GitHub - MasterDNS](https://github.com/masterking32/MasterDnsVPN) |

### ⚠️ Important: Npcap Installation Required

> **🔴 CRITICAL: You MUST install Npcap 1.87 on your Windows machine for masscan to work!**

**Installation Steps:**
1. Download **npcap-1.87.exe** from [https://npcap.com/dist/npcap-1.87.exe](https://npcap.com/dist/npcap-1.87.exe)
3. During installation, ensure these options are checked:
   - ✅ "Install Npcap in WinPcap API-compatible Mode"
4. Complete the installation and restart if prompted

**Why is Npcap required?**
Masscan relies on Npcap (or WinPcap) to send and receive raw network packets at high speeds. Without Npcap, masscan will fail with errors like:
- `FAIL: failed to open adapter`
- `libpcap not found`
- `WinPcap not installed`

### Required Files Structure
```
project-directory/
├── massDNSScanner.py          # Main script
├── masscan.exe                # Masscan executable
├── MasterDnsVPN_Client_*.exe  # VPN client executable
├── client_resolvers.txt       # (Optional) Existing resolvers list
├── tmp/                       # Created automatically
└── output files/              # Generated by script
```

### System Requirements
- **OS**: Windows 10/11 or Windows Server 2016+
- **Npcap**: Version 1.87 (MANDATORY)
- **RAM**: 4GB minimum, 8GB+ recommended
- **Network**: Administrative privileges may be required for masscan
- **Disk**: 100MB+ for log files (depends on scan size)

---

## 🚀 Installation

### Step 1: Install Npcap 1.87 (MANDATORY)
```bash
# Download and install Npcap 1.87
# Direct link: https://npcap.com/dist/npcap-1.87.exe
# MUST be installed BEFORE running masscan!
```

### Step 2: Clone or Download
```bash
git clone https://github.com/mahdmahd/massDNSScanner.git
cd massDNSScanner
```

### Step 3: Install Python Dependencies
*No external Python packages required!* Uses only standard library modules:
- `subprocess`
- `argparse`
- `pathlib`
- `collections`
- `re`

### Step 4: Install Masscan
1. Download masscan for Windows from [official releases](https://github.com/robertdavidgraham/masscan/releases)
2. Extract `masscan.exe` to the project directory
3. Verify masscan works with Npcap:
   ```bash
   .\masscan.exe --version
   ```

### Step 5: Place VPN Client
- Place the `MasterDnsVPN_Client_Windows_AMD64_*.exe` in the project directory
- The script automatically detects the executable based on pattern matching

### Step 6: Verify Installation
```bash
python massDNSScanner.py --help
```

---

## 💻 Usage

### Basic Usage

#### Interactive Mode (Recommended for beginners)
```bash
python massDNSScanner.py
```
You'll be prompted for:
- IP range (e.g., `5.0.0.0/8`)
- Number of rounds (default: 10)

#### Full Automated Scan
```bash
python massDNSScanner.py -r 192.168.0.0/16 -n 20
```

### Command Line Options

| Flag | Long Option | Description | Default |
|------|-------------|-------------|---------|
| `-r` | `--range` | IP range in CIDR notation | *Interactive prompt* |
| `-n` | `--rounds` | Number of VPN client rounds | `10` |
| `-s` | `--skip-masscan` | Skip masscan, use existing resolvers | `False` |
| `-f` | `--resolvers-file` | Resolvers file when skipping masscan | `client_resolvers.txt` |
| `-a` | `--alternative` | Use alternative byte-by-byte reading | `False` |
| | `--no-mac-discovery` | Skip automatic MAC discovery | `False` |
| | `--router-mac` | Manually specify router MAC | *Auto-discovered* |
| | `--analyze-only` | Only analyze existing tmp folder | `False` |
| | `--tmp-folder` | Folder for round results | `tmp` |
| | `--output` | Output file for top DNS results | `top_dnses.txt` |
| | `--top-n` | Number of top DNS servers to show | `10` |

### Usage Examples

#### 1. Scan Entire /8 Subnet
```bash
python massDNSScanner.py -r 5.0.0.0/8 -n 50
```
Scans all ~16 million IPs in the 5.0.0.0/8 range, runs 50 VPN client rounds.

#### 2. Quick Test on Small Range
```bash
python massDNSScanner.py -r 192.168.1.0/24 -n 5
```
Perfect for testing on local networks.

#### 3. Resume/Reanalyze Existing Results
```bash
python massDNSScanner.py --analyze-only --top-n 20
```
Analyzes existing tmp folder results, shows top 20 DNS servers.

#### 4. Skip Masscan with Custom Resolvers
```bash
python massDNSScanner.py -s -f my_resolvers.txt -n 30
```
Uses pre-existing resolver list, runs 30 VPN rounds.

#### 5. Handle Encoding Issues
```bash
python massDNSScanner.py -r 10.0.0.0/8 -a
```
Uses alternative byte-by-byte reading for problematic environments.

#### 6. Manual Router MAC Specification
```bash
python massDNSScanner.py -r 192.168.0.0/16 --router-mac 00:11:22:33:44:55
```
Bypasses automatic gateway discovery.

#### 7. Full Custom Configuration
```bash
python massDNSScanner.py \
  -r 172.16.0.0/12 \
  -n 100 \
  --tmp-folder results \
  --output dns_top50.txt \
  --top-n 50
```

---

## 📁 Output Files

### File Structure After Execution
```
project-directory/
├── client_resolvers_masscan.txt    # Raw masscan output
├── client_resolvers.txt            # Clean IP list (one per line)
├── top_dnses.txt                   # Top DNS servers analysis
└── tmp/
    ├── round_1_results.txt         # VPN client round 1 output
    ├── round_2_results.txt         # VPN client round 2 output
    ├── ...
    └── dns_analysis.txt            # Detailed analysis report
```

### Understanding Output Files

#### `client_resolvers_masscan.txt` (Raw Masscan Output)
```
#masscan
open tcp 53 192.168.1.1 1734567890
open tcp 53 192.168.1.100 1734567891
# end
```

#### `client_resolvers.txt` (Clean IP List)
```
192.168.1.1
192.168.1.100
192.168.1.150
```

#### `top_dnses.txt` (Analysis Results)
```
# Top DNS Servers Analysis
# Analysis Date: 2026-04-19 14:30:22
# Total Files Analyzed: 50
# Total DNS Occurrences: 1247
# Unique DNS Servers: 89
#
# Format: IP_ADDRESS - Frequency - Percentage - Files
#

# 8.8.8.8 - 523 occurrences (41.9%) - found in 48 files
# 1.1.1.1 - 312 occurrences (25.0%) - found in 45 files
# 9.9.9.9 - 156 occurrences (12.5%) - found in 32 files

# IP Addresses (one per line, sorted by frequency):
8.8.8.8
1.1.1.1
9.9.9.9
```

#### `tmp/dns_analysis.txt` (Detailed Report)
Contains comprehensive statistics including:
- Complete ranking of all discovered DNS servers
- Per-file breakdown of DNS server occurrences
- Statistical summary with percentages

---

## 🔍 Troubleshooting

### Common Issues & Solutions

| Issue | Symptom | Solution |
|-------|---------|----------|
| **Npcap not installed** | `FAIL: failed to open adapter` or `libpcap not found` | **Install npcap-1.87.exe** (see Prerequisites section) |
| **Masscan not found** | `masscan.exe not found` | Ensure masscan.exe is in the same directory as the script |
| **Permission denied** | `Failed to run arp -a` | Run as Administrator for ARP table access |
| **Encoding errors** | Unicode decode errors in output | Use `-a` flag for alternative reading method |
| **VPN client hangs** | No "Session init attempt" detection | Try `-a` flag or manually verify VPN client works |
| **No DNS servers found** | Analysis returns empty results | Check tmp folder for files; ensure VPN client is generating logs |
| **Masscan slow** | Scanning taking too long | Adjust `--rate` parameter in script (default: 10000) |

### Npcap-Specific Issues

#### Npcap Installation Failed
```bash
# Solution: Uninstall any existing WinPcap/Npcap first
# 1. Go to Control Panel > Programs and Features
# 2. Uninstall "Npcap" or "WinPcap"
# 3. Reboot
# 4. Install npcap-1.87.exe as Administrator
```

#### Masscan Can't Find Npcap
```bash
# Verify Npcap installation
sc query npcap

# If not running, start the service
net start npcap

# Reinstall Npcap with WinPcap compatibility mode
```

### Common Workarounds

#### 1. ARP Table Empty
```bash
# Manually populate ARP table
ping 192.168.1.1
arp -a
```

#### 2. Masscan Rate Limiting
Edit the script to adjust rate:
```python
"--rate=5000",  # Reduce from 10000 if experiencing packet loss
```

#### 3. VPN Client Detection Issues
Monitor VPN client manually first:
```bash
.\MasterDnsVPN_Client_*.exe
# Watch for "Session init attempt" message
```

---


## ⚠️ DISCLAIMER

<div align="center">

### 🚨 IMPORTANT LEGAL NOTICE 🚨

</div>

**This tool is provided for educational and research purposes only. The authors and contributors are NOT responsible for any misuse, damage, or illegal activities conducted with this software.**

#### By using this software, you acknowledge and agree that:

1. **No Liability**: The creators, contributors, and copyright holders of massDNSScanner **SHALL NOT BE HELD LIABLE** for any direct, indirect, incidental, special, exemplary, or consequential damages (including, but not limited to, procurement of substitute goods or services; loss of use, data, or profits; or business interruption) however caused and on any theory of liability, whether in contract, strict liability, or tort (including negligence or otherwise) arising in any way out of the use of this software, even if advised of the possibility of such damage.

2. **User Responsibility**: **YOU** are solely responsible for complying with all applicable laws, regulations, and terms of service when using this tool. This includes, but is not limited to:
   - Obtaining **EXPLICIT WRITTEN PERMISSION** before scanning any network you do not own
   - Adhering to local, state, and federal laws regarding network scanning
   - Respecting the Computer Fraud and Abuse Act (CFAA) and similar international laws
   - Following the acceptable use policies of your ISP and network providers

3. **Authorized Use Only**: This tool should **ONLY** be used on networks and systems that:
   - You own personally
   - You have explicit written authorization to test
   - Are part of authorized penetration testing engagements
   - Are designated for security research (e.g., bug bounty programs)

4. **No Warranty**: This software is provided **"AS IS"**, without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement.

5. **Legal Consequences**: Unauthorized port scanning and network enumeration may be considered **ILLEGAL** in many jurisdictions and can result in:
   - Criminal charges
   - Civil lawsuits
   - Monetary damages
   - Imprisonment
   - Permanent criminal record

6. **Third-Party Tools**: This software utilizes third-party tools (masscan, Npcap, VPN client). The authors are not responsible for any issues arising from the use of these third-party components.

7. **Indemnification**: You agree to indemnify, defend, and hold harmless the authors, contributors, and copyright holders from and against any and all claims, damages, obligations, losses, liabilities, costs, or debt, and expenses (including but not limited to attorney's fees) arising from:
   - Your use of and access to the software
   - Your violation of any term of this disclaimer
   - Your violation of any third-party right, including without limitation any copyright, property, or privacy right
   - Any claim that your use of the software caused damage to a third party

#### Remember:
> **With great power comes great responsibility. Use this tool ethically and legally.**

**If you are unsure about the legality of your intended use, CONSULT WITH A QUALIFIED ATTORNEY before proceeding.**

---

## 📄 License

This project is licensed under the MIT License - see below for details:

```
MIT License

Copyright (c) 2026 massDNSScanner Contributors
Original concept by Amir

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 🙏 Acknowledgments

- **Amir** - For the original idea and concept that inspired this tool ✨

---

<div align="center">

**⭐ If you find this tool useful, please consider giving it a star! ⭐**

Made with ❤️ by mehdi | Original idea by **Amir**

</div>