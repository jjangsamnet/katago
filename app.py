"""
KataGo REST API Server for Render.com
바둑 AI 서버 - KataGo 엔진 연동
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import threading
import queue
import re
import os
import time

app = Flask(__name__)
CORS(app)  # 모든 도메인에서 접근 허용

# ========================================
# KataGo 엔진 관리
# ========================================

class KataGoEngine:
    def __init__(self):
        self.process = None
        self.lock = threading.Lock()
        self.ready = False
        self.board_size = 19
        self.komi = 6.5
        
    def start(self):
        """KataGo 엔진 시작"""
        try:
            katago_path = os.environ.get('KATAGO_PATH', './katago')
            config_path = os.environ.get('KATAGO_CONFIG', './config.cfg')
            model_path = os.environ.get('KATAGO_MODEL', './model.bin.gz')
            
            cmd = [
                katago_path,
                'gtp',
                '-config', config_path,
                '-model', model_path
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # GTP 초기화 대기
            time.sleep(2)
            
            # 테스트 명령
            response = self._send_command('name')
            if 'KataGo' in response:
                self.ready = True
                print("KataGo 엔진 시작 완료")
                return True
            else:
                print(f"KataGo 시작 실패: {response}")
                return False
                
        except Exception as e:
            print(f"KataGo 시작 오류: {e}")
            return False
    
    def _send_command(self, command):
        """GTP 명령 전송"""
        if not self.process:
            return None
            
        try:
            self.process.stdin.write(command + '\n')
            self.process.stdin.flush()
            
            response = []
            while True:
                line = self.process.stdout.readline()
                if line.strip() == '':
                    if response:
                        break
                else:
                    response.append(line.strip())
                    
            return '\n'.join(response)
        except Exception as e:
            print(f"명령 전송 오류: {e}")
            return None
    
    def set_board_size(self, size):
        """바둑판 크기 설정"""
        with self.lock:
            self.board_size = size
            return self._send_command(f'boardsize {size}')
    
    def set_komi(self, komi):
        """덤 설정"""
        with self.lock:
            self.komi = komi
            return self._send_command(f'komi {komi}')
    
    def clear_board(self):
        """바둑판 초기화"""
        with self.lock:
            return self._send_command('clear_board')
    
    def play_move(self, color, vertex):
        """착수"""
        with self.lock:
            cmd = f'play {color} {vertex}'
            return self._send_command(cmd)
    
    def generate_move(self, color):
        """AI 착수 생성"""
        with self.lock:
            cmd = f'genmove {color}'
            response = self._send_command(cmd)
            if response:
                # "= D4" 형식에서 좌표 추출
                match = re.search(r'=\s*(\w+)', response)
                if match:
                    return match.group(1)
            return None
    
    def get_analysis(self, color, max_visits=100):
        """분석 정보 가져오기"""
        with self.lock:
            # kata-analyze 명령 사용
            cmd = f'kata-analyze {color} {max_visits}'
            self.process.stdin.write(cmd + '\n')
            self.process.stdin.flush()
            
            # 분석 결과 수집 (일정 시간 후 중지)
            time.sleep(1)
            self.process.stdin.write('\n')  # 분석 중지
            self.process.stdin.flush()
            
            response = []
            while True:
                line = self.process.stdout.readline()
                if not line or line.strip() == '':
                    break
                response.append(line.strip())
            
            return self._parse_analysis('\n'.join(response))
    
    def _parse_analysis(self, response):
        """분석 결과 파싱"""
        moves = []
        winrate = 50.0
        score = 0.0
        
        # info move D4 visits 100 winrate 0.55 scoreMean 2.5 ...
        info_pattern = r'info move (\w+) visits (\d+) winrate ([\d.]+) scoreMean ([-\d.]+)'
        
        for match in re.finditer(info_pattern, response):
            move = match.group(1)
            visits = int(match.group(2))
            wr = float(match.group(3)) * 100
            sc = float(match.group(4))
            
            moves.append({
                'move': move,
                'visits': visits,
                'winrate': wr,
                'score': sc
            })
            
            if len(moves) == 1:
                winrate = wr
                score = sc
        
        return {
            'moves': moves[:10],  # 상위 10개
            'winrate': winrate,
            'score': score
        }
    
    def stop(self):
        """엔진 종료"""
        if self.process:
            self._send_command('quit')
            self.process.terminate()
            self.process = None
            self.ready = False


# 전역 엔진 인스턴스
engine = KataGoEngine()


# ========================================
# API 엔드포인트
# ========================================

@app.route('/')
def home():
    return jsonify({
        'name': 'KataGo REST API Server',
        'version': '1.0.0',
        'status': 'running',
        'engine_ready': engine.ready
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'engine_ready': engine.ready
    })


@app.route('/select-move', methods=['POST'])
def select_move():
    """
    AI 착수 선택
    
    Request:
    {
        "board_size": 19,
        "moves": ["D4", "Q16", "D16"],  // 기존 착수 목록
        "komi": 6.5,
        "max_visits": 100
    }
    
    Response:
    {
        "move": "Q4",
        "moves": [...],
        "winrate": 55.5,
        "score": 2.3
    }
    """
    try:
        data = request.get_json()
        
        board_size = data.get('board_size', 19)
        moves = data.get('moves', [])
        komi = data.get('komi', 6.5)
        max_visits = data.get('max_visits', 50)
        
        # 엔진 설정
        engine.set_board_size(board_size)
        engine.set_komi(komi)
        engine.clear_board()
        
        # 기존 착수 재현
        colors = ['B', 'W']
        for i, move in enumerate(moves):
            color = colors[i % 2]
            engine.play_move(color, move)
        
        # 다음 착수할 색상
        next_color = colors[len(moves) % 2]
        
        # AI 착수 생성
        ai_move = engine.generate_move(next_color)
        
        # 분석 정보 (선택적)
        analysis = {'moves': [], 'winrate': 50, 'score': 0}
        
        return jsonify({
            'success': True,
            'move': ai_move,
            'moves': analysis.get('moves', []),
            'winrate': analysis.get('winrate', 50),
            'score': analysis.get('score', 0)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/analyze', methods=['POST'])
def analyze():
    """
    현재 국면 분석
    
    Request:
    {
        "board_size": 19,
        "moves": ["D4", "Q16"],
        "komi": 6.5,
        "max_visits": 100
    }
    """
    try:
        data = request.get_json()
        
        board_size = data.get('board_size', 19)
        moves = data.get('moves', [])
        komi = data.get('komi', 6.5)
        max_visits = data.get('max_visits', 100)
        
        engine.set_board_size(board_size)
        engine.set_komi(komi)
        engine.clear_board()
        
        colors = ['B', 'W']
        for i, move in enumerate(moves):
            color = colors[i % 2]
            engine.play_move(color, move)
        
        next_color = colors[len(moves) % 2]
        analysis = engine.get_analysis(next_color, max_visits)
        
        return jsonify({
            'success': True,
            **analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/play', methods=['POST'])
def play_move():
    """
    착수 실행 (세션 유지)
    """
    try:
        data = request.get_json()
        color = data.get('color', 'B')
        vertex = data.get('vertex', 'pass')
        
        result = engine.play_move(color, vertex)
        
        return jsonify({
            'success': True,
            'result': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# 간단한 폴백 AI (KataGo 없이 동작)
# ========================================

class SimpleAI:
    """KataGo가 없을 때 사용하는 간단한 AI"""
    
    def __init__(self):
        self.board_size = 19
        self.board = None
        
    def init_board(self, size):
        self.board_size = size
        self.board = [[0] * size for _ in range(size)]
    
    def play(self, color, vertex):
        if vertex.lower() == 'pass':
            return True
        
        x, y = self._parse_vertex(vertex)
        if x is not None:
            self.board[y][x] = 1 if color.upper() == 'B' else 2
            return True
        return False
    
    def _parse_vertex(self, vertex):
        try:
            col = vertex[0].upper()
            row = int(vertex[1:])
            
            x = ord(col) - ord('A')
            if x >= 8:  # I 제외
                x -= 1
            y = self.board_size - row
            
            return x, y
        except:
            return None, None
    
    def _to_vertex(self, x, y):
        col = chr(ord('A') + (x if x < 8 else x + 1))
        row = self.board_size - y
        return f"{col}{row}"
    
    def generate_move(self, color):
        """간단한 휴리스틱 기반 착수"""
        best_score = -1
        best_move = 'pass'
        
        center = self.board_size // 2
        
        # 화점 우선
        star_points = self._get_star_points()
        for x, y in star_points:
            if self.board[y][x] == 0:
                return self._to_vertex(x, y)
        
        # 빈 곳 중 중앙에 가까운 곳
        for y in range(self.board_size):
            for x in range(self.board_size):
                if self.board[y][x] == 0:
                    score = self.board_size - abs(x - center) - abs(y - center)
                    score += self._count_neighbors(x, y) * 5
                    
                    if score > best_score:
                        best_score = score
                        best_move = self._to_vertex(x, y)
        
        return best_move
    
    def _get_star_points(self):
        if self.board_size == 19:
            return [(3,3), (3,9), (3,15), (9,3), (9,9), (9,15), (15,3), (15,9), (15,15)]
        elif self.board_size == 13:
            return [(3,3), (3,9), (6,6), (9,3), (9,9)]
        else:
            return [(2,2), (2,6), (4,4), (6,2), (6,6)]
    
    def _count_neighbors(self, x, y):
        count = 0
        for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.board_size and 0 <= ny < self.board_size:
                if self.board[ny][nx] != 0:
                    count += 1
        return count


simple_ai = SimpleAI()


@app.route('/simple-move', methods=['POST'])
def simple_move():
    """
    간단한 AI 착수 (KataGo 없이 동작)
    """
    try:
        data = request.get_json()
        
        board_size = data.get('board_size', 19)
        moves = data.get('moves', [])
        
        simple_ai.init_board(board_size)
        
        colors = ['B', 'W']
        for i, move in enumerate(moves):
            color = colors[i % 2]
            simple_ai.play(color, move)
        
        next_color = colors[len(moves) % 2]
        ai_move = simple_ai.generate_move(next_color)
        
        return jsonify({
            'success': True,
            'move': ai_move,
            'winrate': 50,
            'score': 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ========================================
# 서버 시작
# ========================================

def init_engine():
    """엔진 초기화 (백그라운드)"""
    # KataGo 바이너리가 있으면 시작
    katago_path = os.environ.get('KATAGO_PATH', './katago')
    if os.path.exists(katago_path):
        engine.start()
    else:
        print("KataGo 바이너리 없음 - Simple AI 모드로 동작")


if __name__ == '__main__':
    # 엔진 초기화
    init_thread = threading.Thread(target=init_engine)
    init_thread.start()
    
    # Flask 서버 시작
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
