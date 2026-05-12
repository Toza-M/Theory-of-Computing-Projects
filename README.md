# ⚙️ Theory of Computing: Projects Repository

## 📚 Course Overview
Welcome to our Theory of Computing repository! This workspace contains a collection of interactive algorithms and tools built to explore the mathematical foundations of computer science, specifically focusing on Automata Theory. Throughout this course, we are building practical implementations of theoretical machines and language processors.

---

## 👥 Team Members
* **Zyad Mohamed** 
* **Rowayda Hatem**
* **Maya Hatem**
* **Mazen Ayman**

---

## 🚀 Overview of Project 1: Interactive Regex to Automata Compiler
**Status:** Completed ✅

Project 1 is a fully interactive, web-based compiler that translates standard Regular Expressions into mathematically accurate Non-Deterministic Finite Automata (NFA) and Deterministic Finite Automata (DFA). 

To comply with strict academic guidelines, the core algorithms were built from scratch using **pure Python** (no external libraries). We then used **PyScript** to seamlessly execute this backend logic directly inside a modern web browser, visualizing the state machines in real-time.

**Key Features:**
* **Explicit Concatenation:** Automatically preprocesses standard regex strings (e.g., `(a|b)*c`) to insert implicit concatenation operators (`.`).
* **Shunting-Yard Parser:** Converts Infix regex expressions into Postfix notation for stack evaluation.
* **Thompson's Construction (NFA):** Modular logic that generates state machines for Literals, Concatenation, Union, and Kleene Star operations using ε-transitions.
* **Subset Construction (DFA):** Algorithmically groups subsets of NFA states via ε-closures to generate an optimized Deterministic Finite Automaton.

---

## 💻 Tech Stack
* **Backend Logic:** Pure Python 3 (Object-Oriented Data Structures)
* **Web Integration:** PyScript (Python in HTML)
* **Frontend UI:** HTML5, CSS3, Vanilla JS
* **Graph Rendering:** Viz.js (DOT Language)

---

## 🛠️ How to Run Project 1

Because this project relies on **PyScript** to load Python environments in the browser, modern web browsers will block the scripts if you simply double-click the HTML files (due to CORS security policies). **You must serve the files through a local web server.**

**Method 1: Using VS Code**
1. Open this repository folder in Visual Studio Code.
2. Install the **Live Server** extension by Ritwick Dey.
3. Navigate to `Project_1/Home_Page.html`.
4. Right-click the file and select **Open with Live Server**. Your default browser will open automatically.

**Method 2: Using Python's Built-in Server**
1. Open your terminal or command prompt.
2. Navigate to the `Project_1` directory.
3. Run the following command: `python -m http.server 8000`
4. Open your web browser and navigate to: `http://localhost:8000/Home_Page.html`

---

## 🌐 Overview of Project 2: The Language Studio — CFG Parser & Parse Tree Visualizer
**Status:** Completed ✅
 
Project 2 is a fully interactive, web-based tool that takes any Context-Free Grammar (CFG), converts it into Chomsky Normal Form (CNF), and determines whether a given string belongs to the language — visualizing the full parse tree in real-time.
As with Project 1, all core algorithms were implemented from scratch in **pure Python** (no external libraries) and executed directly in the browser via **PyScript**.
 
**Key Features:**
* **CNF Conversion Pipeline:** A rigorous 6-step algorithm that normalizes any CFG into strict Chomsky Normal Form, handling epsilon-productions, unit productions, useless symbols, mixed bodies, and long productions.
* **CYK Parser:** An O(n³ · |G|) dynamic programming parser that fills a triangular table of non-terminals and determines string membership.
* **Parse Tree Backtracking:** Full reconstruction of one (or all) parse trees from CYK back-pointers, with ambiguity detection and reporting.
* **Live Visualization:** The resulting parse tree is serialized to JSON, converted to DOT language, and rendered as an interactive SVG graph via Viz.js.
---
 
## 💻 Tech Stack
* **Backend Logic:** Pure Python 3 (Object-Oriented Data Structures)
* **Web Integration:** PyScript (Python in HTML)
* **Frontend UI:** HTML5, CSS3, Vanilla JS
* **Graph Rendering:** Viz.js (DOT Language)
---
 
## 🛠️ How to Run
 
Because these projects rely on **PyScript** to load Python environments in the browser, modern web browsers will block the scripts if you simply double-click the HTML files (due to CORS security policies). **You must serve the files through a local web server.**
 
**Method 1: Using VS Code**
1. Open this repository folder in Visual Studio Code.
2. Install the **Live Server** extension by Ritwick Dey.
3. Navigate to the desired project's HTML file (e.g., `Project_1/Home_Page.html` or `Project_2/index.html`).
4. Right-click the file and select **Open with Live Server**. Your default browser will open automatically.
**Method 2: Using Python's Built-in Server**
1. Open your terminal or command prompt.
2. Navigate to the desired project's directory (e.g., `Project_1` or `Project_2`).
3. Run the following command: `python -m http.server 8000`
4. Open your web browser and navigate to the appropriate URL:
   * Project 1: `http://localhost:8000/Home_Page.html`
   * Project 2: `http://localhost:8000/index.html`
---

## 📂 Repository Structure

Because this repository houses multiple coursework projects, it is organized into dedicated directories:

```text
Theory-of-Computing-Projects/
│
├── README.md                 
├── .gitignore
│
├── Project_1/                # Regex to NFA & DFA Compiler
│   ├── Home_Page.html        # Interactive landing page and input handler
│   ├── NFA.html              # NFA visualization and PyScript logic
│   ├── NFA_Back.py           # Core Thompson's Construction algorithms
│   ├── DFA_Back.py           # Subset Construction algorithms
│   ├── Style_of_NFA.css      # UI Styling
│   ├── Style_of_home_page.css# Home Page Styling
│   └── Background.jpg        # Shared background asset
│
├── Project_2/                    # CFG Parser & Parse Tree Visualizer
│   ├── index.html                # Main application (UI + JS + PyScript bridge)
│   ├── CNF_Converter.py          # CFG → CNF conversion pipeline (6-step algorithm)
│   ├── CYK_Converter.py          # CYK parser with parse-tree backtracking
│   └── Background.jpg            # Shared background asset
│
└── Project_3/                    # 🚧 Coming Soon
```
