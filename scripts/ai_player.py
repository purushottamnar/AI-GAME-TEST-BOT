import math
import pygame
import os
import time

class AIPlayer:
    def __init__(self, game):
        self.game = game
        self.reaction_time = 10  # frames to wait before reacting to threats
        self.threat_memory = []  # remember projectile positions
        self.last_action_time = 0
        self.path = []  # for pathfinding
        self.target_enemy = None
        self.safe_platform = None
        self.last_pos = None
        self.stuck_timer = 0
        self.last_jump_time = 0
        self.last_dash_time = 0
        self.debug = True  # Enable debug printing
        self.current_target = None
        self.last_target = None  # Initialize last_target
        self.target_lock_time = 0
        self.target_lock_duration = 2000  # Lock onto current target for 2 seconds
        self.periodic_jump_interval = 3000  # Jump every 3 seconds (3000ms)
        self.last_periodic_jump = 0  # Track last periodic jump time
        self.fall_start_y = None  # Track fall start position
        self.max_safe_fall = 200  # Reduced maximum safe fall distance to 200 pixels
        self.fall_bug_detected = False  # Track if fall bug was detected
        self.fall_bug_count = 0  # Count how many times the bug has been detected
        self.last_fall_report_time = 0  # Track when we last reported the bug
        self.fall_start_time = None
        self.max_fall_time = 15000  # 15 seconds in milliseconds for no platform detection
        self.no_platform_start_time = None  # Track when we last saw a platform
        self.continuous_fall_reported = False
        self.last_y_pos = None
        self.falling_speed = 0
        self.fall_duration = 0
        self.jump_attempts = 0  # Track number of jumps
        self.max_jump_attempts = 30  # Maximum allowed jumps before reporting bug
        # Attack detection variables
        self.attack_range = 100  # Range within which player should attack
        self.time_in_range = 0  # Time spent near enemy without attacking
        self.max_time_without_attack = 240  # 4 seconds (60 frames/second)
        self.attack_bug_reported = False
        self.enemies_in_range = 0
        self.last_attack_time = 0
        self.bug_report_count = 0  # Track number of bug reports generated
        
        # Bug detection variables
        self.bugs_detected = {
            'combat': {'active': False, 'details': None, 'time': 0},
            'fall': {'active': False, 'details': None, 'time': 0},
            'decision': {'active': False, 'details': None, 'time': 0},
            'bullet_survival': {'active': False, 'details': None, 'time': 0}
        }
        self.last_target_switch = 0
        self.target_switches = 0
        
        # Bullet hit tracking
        self.bullet_hits = 0
        self.max_bullet_hits = 3  # Maximum hits before player should die
        self.last_hit_time = 0
        self.hit_invulnerability_time = 1000  # 1 second invulnerability after hit
        self.bullet_survival_reported = False
        self.jump_cooldown = 500  # 500ms cooldown between jumps
        self.min_jump_height = 32  # Minimum height for considering a jump
        self.max_jump_height = 160  # Maximum safe jump height
        self.can_double_jump = True  # Track if double jump is available
        self.last_ground_time = 0  # Track when we last touched ground
        self.platform_scan_range = 200  # How far to scan for platforms
        
        # Add session tracking
        self.session_start_time = time.strftime('%Y-%m-%d %H:%M:%S')
        self.session_id = int(time.time())
        self.bugs_this_session = {
            'combat': 0,
            'fall': 0,
            'decision': 0,
            'bullet_survival': 0
        }

    def get_nearest_enemy(self):
        current_time = pygame.time.get_ticks()
        
        # Keep current target if lock time hasn't expired and target still exists
        if (self.current_target and 
            current_time - self.target_lock_time < self.target_lock_duration and 
            self.current_target in self.game.enemies):
            
            player_pos = self.game.player.rect().center
            dist = math.sqrt((player_pos[0] - self.current_target.pos[0])**2 + 
                           (player_pos[1] - self.current_target.pos[1])**2)
            height_diff = abs(player_pos[1] - self.current_target.pos[1])
            
            # Release target lock if height difference becomes too large
            if height_diff > 60:
                if self.debug:
                    print(f"Releasing target lock - height difference too large: {height_diff}")
                self.current_target = None
            else:
                if self.debug:
                    print(f"Pursuing locked target at distance: {dist}, height diff: {height_diff}")
                return self.current_target, dist

        if not self.game.enemies:
            if self.debug:
                print("No enemies found")
            return None, float('inf')
        
        player_pos = self.game.player.rect().center
        nearest = None
        min_score = float('inf')  # Lower score is better
        
        for enemy in self.game.enemies:
            dist = math.sqrt((player_pos[0] - enemy.pos[0])**2 + 
                           (player_pos[1] - enemy.pos[1])**2)
            height_diff = abs(player_pos[1] - enemy.pos[1])
            
            # Score based on both distance and height difference
            # Heavily penalize height differences over 60 pixels
            height_penalty = height_diff * 2 if height_diff <= 60 else height_diff * 10
            score = dist + height_penalty
            
            if score < min_score:
                min_score = score
                nearest = enemy
        
        # Only lock onto target if height difference is acceptable
        if nearest:
            height_diff = abs(player_pos[1] - nearest.pos[1])
            if height_diff <= 60:
                self.current_target = nearest
                self.target_lock_time = current_time
                if self.debug:
                    print(f"New target acquired! Distance: {min_score}, Height diff: {height_diff}")
            else:
                if self.debug:
                    print(f"Target too far in height ({height_diff}px), seeking better target")
                return None, float('inf')
        
        return nearest, min_score

    def is_position_safe(self, pos):
        # Check if position has ground below
        ground_check = self.game.tilemap.solid_check((pos[0], pos[1] + 32))
        if not ground_check:
            return False
            
        # Check for projectiles near position
        for proj in self.game.projectiles:
            proj_pos = proj[0]
            dist = math.sqrt((pos[0] - proj_pos[0])**2 + (pos[1] - proj_pos[1])**2)
            if dist < 40:  # danger zone
                return False
                
        return True

    def find_safe_platform(self):
        player_pos = self.game.player.rect().center
        search_radius = 100
        
        # Sample points in a grid pattern
        for x in range(player_pos[0] - search_radius, player_pos[0] + search_radius, 32):
            for y in range(player_pos[1] - search_radius, player_pos[1] + search_radius, 32):
                if self.is_position_safe((x, y)):
                    return (x, y)
                    
        return None

    def should_dodge(self):
        player_rect = self.game.player.rect()
        dodge_radius = 30   # Reduced from 60 to 30 pixels for more precise dodging
        
        # Combine both enemy and player projectiles for detection
        all_projectiles = []
        
        # Add enemy projectiles
        for proj in self.game.projectiles:
            all_projectiles.append((proj[0], proj[1], "enemy"))
            
        # Add player projectiles if they exist
        if hasattr(self.game, 'player_projectiles'):
            for proj in self.game.player_projectiles:
                all_projectiles.append((proj[0], proj[1], "player"))
        
        for proj in all_projectiles:
            proj_pos = proj[0]
            proj_dir = proj[1]
            proj_type = proj[2]
            
            # Calculate distances
            dist_x = proj_pos[0] - player_rect.centerx
            dist_y = proj_pos[1] - player_rect.centery
            
            # Calculate direct distance (radius) to bullet
            direct_distance = math.sqrt(dist_x**2 + dist_y**2)
            
            # Check if bullet is at same height (within 20 pixels vertically)
            same_height = abs(dist_y) < 20
            
            # Only consider bullets that are moving towards the player
            if (proj_dir > 0 and dist_x > 0) or (proj_dir < 0 and dist_x < 0):
                time_to_impact = abs(dist_x / proj_dir) if proj_dir != 0 else float('inf')
                
                # Debug information about bullet
                if self.debug and direct_distance < dodge_radius:
                    print(f"{proj_type.capitalize()} bullet detected:")
                    print(f"Distance: {direct_distance:.1f}px")
                    print(f"Height difference: {abs(dist_y):.1f}px")
                    print(f"Time to impact: {time_to_impact:.1f}")
                
                # Check if bullet is within dodge radius and at same height
                if direct_distance < dodge_radius and same_height:
                    if self.debug:
                        print(f"!!! DODGE NEEDED - {proj_type} bullet at {direct_distance:.1f}px, same height !!!")
                    return True, proj_dir, time_to_impact, True
                    
        return False, 0, 0, False

    def is_platform_above(self):
        player = self.game.player
        check_height = 64  # Check up to 64 pixels above
        check_width = 32   # Check 32 pixels wide
        
        # Check for platform above
        for y_offset in range(16, check_height, 16):
            left_point = (player.pos[0] - check_width // 2, player.pos[1] - y_offset)
            right_point = (player.pos[0] + check_width // 2, player.pos[1] - y_offset)
            
            if (self.game.tilemap.solid_check(left_point) or 
                self.game.tilemap.solid_check(right_point)):
                if self.debug:
                    print(f"Found platform {y_offset}px above")
                return True, y_offset
        return False, 0

    def is_near_edge(self):
        player = self.game.player
        check_distance = 32  # Check 32 pixels ahead
        check_depth = 48    # Check 48 pixels down for ground
        
        # Check both left and right sides
        left_edge = False
        right_edge = False
        
        # Check left edge
        left_ground = self.game.tilemap.solid_check((player.pos[0] - check_distance, player.pos[1] + check_depth))
        if not left_ground and player.collisions['down']:
            left_edge = True
            
        # Check right edge
        right_ground = self.game.tilemap.solid_check((player.pos[0] + check_distance, player.pos[1] + check_depth))
        if not right_ground and player.collisions['down']:
            right_edge = True
            
        if left_edge or right_edge:
            if self.debug:
                print(f"Edge detected! Left: {left_edge}, Right: {right_edge}")
            return True, left_edge, right_edge
            
        return False, False, False

    def check_platform_below(self):
        player = self.game.player
        check_depth = 128  # Check up to 128 pixels below
        check_width = 32   # Check 32 pixels wide
        
        # Check for platform below
        for y_offset in range(32, check_depth, 16):
            left_point = (player.pos[0] - check_width // 2, player.pos[1] + y_offset)
            right_point = (player.pos[0] + check_width // 2, player.pos[1] + y_offset)
            
            if (self.game.tilemap.solid_check(left_point) or 
                self.game.tilemap.solid_check(right_point)):
                if self.debug:
                    print(f"Found platform {y_offset}px below")
                return True, y_offset
        if self.debug:
            print("No platform detected below!")
        return False, 0

    def detect_immortal_fall_bug(self):
        player = self.game.player
        current_time = pygame.time.get_ticks()
        current_y = player.pos[1]

        # Check for platform below player
        has_platform = False
        check_depth = 200  # Check up to 200 pixels below
        player_pos = player.pos
        
        # Scan for platforms below
        for y_offset in range(32, check_depth, 16):
            check_pos = (player_pos[0], player_pos[1] + y_offset)
            if self.game.tilemap.solid_check(check_pos):
                has_platform = True
                break

        # Start tracking time if no platform is found
        if not has_platform and not player.collisions['down']:
            if self.no_platform_start_time is None:
                self.no_platform_start_time = current_time
                if self.debug:
                    print("No platform detected below, starting timer")
        else:
            # Reset timer if platform is found or player is on ground
            if self.no_platform_start_time is not None:
                if self.debug:
                    print("Platform detected or landed, resetting timer")
            self.no_platform_start_time = None
            self.continuous_fall_reported = False

        # Calculate falling metrics
        if self.last_y_pos is not None:
            self.falling_speed = current_y - self.last_y_pos

        # Check for no platform duration
        if self.no_platform_start_time is not None:
            no_platform_duration = (current_time - self.no_platform_start_time) / 1000  # Convert to seconds
            
            # Detect fall bug if no platform for 15 seconds
            if no_platform_duration >= 15.0 and not self.continuous_fall_reported:
                self.continuous_fall_reported = True
                self.bugs_detected['fall'] = {
                    'active': True,
                    'details': {
                        'type': 'No Platform Fall Bug',
                        'duration': f"{no_platform_duration:.1f}s",
                        'fall_speed': f"{self.falling_speed:.1f}px/frame",
                        'current_y': f"{current_y:.1f}",
                        'distance_checked': f"{check_depth}px",
                        'time': current_time
                    }
                }
                if self.debug:
                    print(f"No platform fall bug detected! Duration: {no_platform_duration:.1f}s")

        # Check for excessive jump attempts during fall
        if not player.collisions['down'] and self.jump_attempts >= self.max_jump_attempts:
            self.bugs_detected['fall'] = {
                'active': True,
                'details': {
                    'type': 'Excessive Jump Bug',
                    'jump_attempts': self.jump_attempts,
                    'max_attempts': self.max_jump_attempts,
                    'fall_speed': f"{self.falling_speed:.1f}px/frame",
                    'current_y': f"{current_y:.1f}",
                    'time': current_time
                }
            }
            if self.debug:
                print(f"Excessive jump bug detected! Attempts: {self.jump_attempts}/{self.max_jump_attempts}")
        
        # Update last y position
        self.last_y_pos = current_y

    def detect_attack_bug(self):
        player = self.game.player
        current_time = pygame.time.get_ticks()
        
        # Check for enemies in attack range
        enemies_in_range = 0
        for enemy in self.game.enemies:
            dist_x = abs(enemy.pos[0] - player.pos[0])
            dist_y = abs(enemy.pos[1] - player.pos[1])
            
            if dist_x < self.attack_range and dist_y < 50:
                enemies_in_range += 1
        
        self.enemies_in_range = enemies_in_range
        
        # If enemies are in range, increment timer
        if enemies_in_range > 0:
            self.time_in_range += 1
            
            # Report bug if player hasn't attacked for too long
            if self.time_in_range > self.max_time_without_attack and not self.attack_bug_reported:
                self.attack_bug_reported = True
                self.bugs_detected['combat'] = {
                    'active': True,
                    'details': {
                        'type': 'Combat Inaction',
                        'enemies_in_range': enemies_in_range,
                        'time_without_attack': f"{self.time_in_range/60:.1f}s",
                        'attack_range': self.attack_range,
                        'time': current_time
                    }
                }
                if self.debug:
                    print(f"Combat bug detected! No attack for {self.time_in_range/60:.1f}s with {enemies_in_range} enemies")
        else:
            # Reset timer if no enemies in range
            self.time_in_range = 0
            self.attack_bug_reported = False

    def detect_bullet_survival_bug(self):
        current_time = pygame.time.get_ticks()
        
        # Check for bullet collisions
        for proj in self.game.projectiles:
            proj_rect = pygame.Rect(proj[0][0] - 4, proj[0][1] - 4, 8, 8)
            player_rect = self.game.player.rect()
            
            if player_rect.colliderect(proj_rect):
                # Only count hit if invulnerability period is over
                if current_time - self.last_hit_time > self.hit_invulnerability_time:
                    self.bullet_hits += 1
                    self.last_hit_time = current_time
                    
                    if self.bullet_hits >= self.max_bullet_hits and not self.bullet_survival_reported:
                        self.bullet_survival_reported = True
                        self.bugs_detected['bullet_survival'] = {
                            'active': True,
                            'details': {
                                'type': 'Bullet Hit Survival',
                                'hits_taken': self.bullet_hits,
                                'max_hits': self.max_bullet_hits,
                                'time_window': f"{(current_time - self.last_hit_time)/1000:.1f}s"
                            },
                            'time': current_time
                        }
                        if self.debug:
                            print(f"Bullet survival bug detected! Hits: {self.bullet_hits}")

    def detect_decision_bug(self):
        current_time = pygame.time.get_ticks()
        
        # Track target switching
        if self.current_target != self.last_target:
            if current_time - self.last_target_switch < 1000:  # Less than 1 second since last switch
                self.target_switches += 1
                if self.target_switches > 3:  # More than 3 quick switches
                    self.bugs_detected['decision'] = {
                        'active': True,
                        'details': {
                            'type': 'Rapid Target Switching',
                            'switches': self.target_switches,
                            'time_window': '1 second'
                        },
                        'time': current_time
                    }
            else:
                self.target_switches = 0
            
            self.last_target_switch = current_time
        
        self.last_target = self.current_target

    def generate_bug_report(self):
        try:
            timestamp = pygame.time.get_ticks()
            
            # Create Logs directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            logs_dir = os.path.join(parent_dir, "Logs")
            os.makedirs(logs_dir, exist_ok=True)
            
            # Use a single file for all bugs with session tracking
            filename = os.path.join(logs_dir, "gameplay_bug_history.html")
            
            # Generate bug summaries for new bugs
            new_bug_summaries = []
            active_bugs = 0
            
            for bug_type, data in self.bugs_detected.items():
                if data['active']:
                    active_bugs += 1
                    self.bugs_this_session[bug_type] += 1
                    details = data['details']
                    bug_time = time.strftime('%Y-%m-%d %H:%M:%S')
                    game_time = f"{timestamp/1000:.1f}s"
                    
                    # Add session information to each bug entry
                    session_info = f"""
                        <div class="session-info">
                            <span class="session-id">Session #{self.session_id}</span>
                            <span class="session-start">Started: {self.session_start_time}</span>
                        </div>
                    """
                    
                    if bug_type == 'bullet_survival':
                        new_bug_summaries.append(f"""
                            <div class="bug-entry">
                                <div class="bug-card bullet-survival">
                                    {session_info}
                                    <div class="bug-header">
                                        <h3>🎯 Bullet Survival Bug #{self.bugs_this_session[bug_type]}</h3>
                                        <div class="time-info">
                                            <span class="game-time">Game Time: {game_time}</span>
                                            <span class="real-time">{bug_time}</span>
                                        </div>
                                    </div>
                                    <div class="bug-content">
                                        <p class="bug-description">Player survived excessive bullet hits</p>
                                        <div class="bug-metrics">
                                            <div class="metric">
                                                <span class="value">{details['hits_taken']}/{details['max_hits']}</span>
                                                <span class="label">Hits Survived</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['time_window']}</span>
                                                <span class="label">Time Window</span>
                                            </div>
                                        </div>
                                        <div class="bug-analysis">
                                            <p>Player should have died after {details['max_hits']} hits</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """)
                    elif bug_type == 'combat':
                        new_bug_summaries.append(f"""
                            <div class="bug-entry">
                                <div class="bug-card combat">
                                    {session_info}
                                    <div class="bug-header">
                                        <h3>🗡️ Combat Inaction Bug #{self.bugs_this_session[bug_type]}</h3>
                                        <div class="time-info">
                                            <span class="game-time">Game Time: {game_time}</span>
                                            <span class="real-time">{bug_time}</span>
                                        </div>
                                    </div>
                                    <div class="bug-content">
                                        <p class="bug-description">AI failed to engage nearby enemies</p>
                                        <div class="bug-metrics">
                                            <div class="metric">
                                                <span class="value">{details['enemies_in_range']}</span>
                                                <span class="label">Enemies</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['time_without_attack']}</span>
                                                <span class="label">No Attack</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['attack_range']}px</span>
                                                <span class="label">Range</span>
                                            </div>
                                        </div>
                                        <div class="bug-analysis">
                                            <p>AI should attack when enemies are within {details['attack_range']} pixels</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """)
                    elif bug_type == 'decision':
                        new_bug_summaries.append(f"""
                            <div class="bug-entry">
                                <div class="bug-card decision">
                                    {session_info}
                                    <div class="bug-header">
                                        <h3>🤔 Decision Making Bug #{self.bugs_this_session[bug_type]}</h3>
                                        <div class="time-info">
                                            <span class="game-time">Game Time: {game_time}</span>
                                            <span class="real-time">{bug_time}</span>
                                        </div>
                                    </div>
                                    <div class="bug-content">
                                        <p class="bug-description">{details['type']}</p>
                                        <div class="bug-metrics">
                                            <div class="metric">
                                                <span class="value">{details['switches']}</span>
                                                <span class="label">Target Switches</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['time_window']}</span>
                                                <span class="label">Time Window</span>
                                            </div>
                                        </div>
                                        <div class="bug-analysis">
                                            <p>AI is switching targets too frequently</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """)
                    elif bug_type == 'fall':
                        new_bug_summaries.append(f"""
                            <div class="bug-entry">
                                <div class="bug-card fall">
                                    {session_info}
                                    <div class="bug-header">
                                        <h3>💀 Immortal Fall Bug #{self.bugs_this_session[bug_type]}</h3>
                                        <div class="time-info">
                                            <span class="game-time">Game Time: {game_time}</span>
                                            <span class="real-time">{bug_time}</span>
                                        </div>
                                    </div>
                                    <div class="bug-content">
                                        <p class="bug-description">{details['type']}</p>
                                        <div class="bug-metrics">
                                            <div class="metric">
                                                <span class="value">{details.get('duration', 'N/A')}</span>
                                                <span class="label">Fall Duration</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['fall_speed']}</span>
                                                <span class="label">Fall Speed</span>
                                            </div>
                                            <div class="metric">
                                                <span class="value">{details['current_y']}</span>
                                                <span class="label">Y Position</span>
                                            </div>
                                        </div>
                                        <div class="bug-analysis">
                                            <p>Player should not survive long falls without platforms</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        """)

            # Read existing content
            existing_content = ""
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_content = f.read()
            except FileNotFoundError:
                existing_content = ""

            # Extract existing bug entries
            existing_bugs = ""
            if existing_content:
                start_idx = existing_content.find('<!-- BUG_ENTRIES_START -->')
                end_idx = existing_content.find('<!-- BUG_ENTRIES_END -->')
                if start_idx != -1 and end_idx != -1:
                    existing_bugs = existing_content[start_idx + len('<!-- BUG_ENTRIES_START -->'):end_idx]

            # Combine new and existing bugs
            all_bugs = ''.join(new_bug_summaries) + existing_bugs

            # Add session-specific styling
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Gameplay Bug History</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #1e1e1e;
            color: #ffffff;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background-color: #2d2d2d;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2);
        }}
        .header h1 {{
            margin: 0;
            color: #ff4444;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        .bug-entry {{
            margin-bottom: 20px;
        }}
        .bug-card {{
            background-color: #2d2d2d;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .bug-header {{
            padding: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .time-info {{
            text-align: right;
        }}
        .game-time {{
            font-size: 0.9em;
            color: #4CAF50;
            display: block;
        }}
        .real-time {{
            font-size: 0.8em;
            color: #888;
        }}
        .bug-content {{
            padding: 15px;
        }}
        .bug-description {{
            font-size: 1.1em;
            margin: 0 0 15px 0;
        }}
        .bug-metrics {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 15px;
            margin: 15px 0;
        }}
        .metric {{
            text-align: center;
            background-color: #363636;
            padding: 10px;
            border-radius: 6px;
        }}
        .metric .value {{
            font-size: 1.2em;
            font-weight: bold;
            color: #4CAF50;
            display: block;
        }}
        .metric .label {{
            font-size: 0.8em;
            color: #888;
            margin-top: 5px;
        }}
        .bug-analysis {{
            background-color: #363636;
            padding: 10px;
            border-radius: 6px;
            margin-top: 15px;
        }}
        .bug-analysis p {{
            margin: 0;
            color: #888;
        }}
        .bug-card.combat {{ border-left: 4px solid #dc3545; }}
        .bug-card.combat .value {{ color: #dc3545; }}
        .bug-card.decision {{ border-left: 4px solid #007bff; }}
        .bug-card.decision .value {{ color: #007bff; }}
        .bug-card.bullet-survival {{ border-left: 4px solid #ffc107; }}
        .bug-card.bullet-survival .value {{ color: #ffc107; }}
        .bug-card.fall {{ border-left: 4px solid #28a745; }}
        .bug-card.fall .value {{ color: #28a745; }}
        .stats {{
            background-color: #2d2d2d;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-around;
            align-items: center;
        }}
        .stat-item {{
            text-align: center;
        }}
        .stat-value {{
            font-size: 24px;
            font-weight: bold;
            color: #4CAF50;
        }}
        .stat-label {{
            font-size: 0.9em;
            color: #888;
        }}
        .timestamp {{
            text-align: right;
            color: #888;
            margin-top: 20px;
            font-size: 0.9em;
        }}
        .session-info {{
            background-color: #363636;
            padding: 10px;
            margin: -15px -15px 15px -15px;
            border-bottom: 1px solid #444;
            font-size: 0.9em;
            color: #888;
            display: flex;
            justify-content: space-between;
        }}
        .session-id {{
            font-weight: bold;
            color: #4CAF50;
        }}
        .session-start {{
            color: #888;
        }}
        .bug-summary {{
            background-color: #2d2d2d;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }}
        .bug-summary h2 {{
            color: #4CAF50;
            margin-top: 0;
        }}
        .bug-type-count {{
            display: inline-block;
            padding: 5px 10px;
            margin: 5px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .bug-type-count.combat {{ background-color: #dc354522; color: #dc3545; }}
        .bug-type-count.fall {{ background-color: #28a74522; color: #28a745; }}
        .bug-type-count.decision {{ background-color: #007bff22; color: #007bff; }}
        .bug-type-count.bullet {{ background-color: #ffc10722; color: #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🐛 Gameplay Bug History</h1>
            <p>Complete record of all detected bugs during gameplay</p>
        </div>

        <div class="bug-summary">
            <h2>Current Session Summary</h2>
            <p>Session #{self.session_id} started at {self.session_start_time}</p>
            <div>
                <span class="bug-type-count combat">Combat Bugs: {self.bugs_this_session['combat']}</span>
                <span class="bug-type-count fall">Fall Bugs: {self.bugs_this_session['fall']}</span>
                <span class="bug-type-count decision">Decision Bugs: {self.bugs_this_session['decision']}</span>
                <span class="bug-type-count bullet">Bullet Bugs: {self.bugs_this_session['bullet_survival']}</span>
            </div>
        </div>

        <div class="stats">
            <div class="stat-item">
                <div class="stat-value">{self.bug_report_count + active_bugs}</div>
                <div class="stat-label">Total Bugs</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{active_bugs}</div>
                <div class="stat-label">New Bugs</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{timestamp/1000:.1f}s</div>
                <div class="stat-label">Game Time</div>
            </div>
        </div>

        <!-- BUG_ENTRIES_START -->
        {all_bugs}
        <!-- BUG_ENTRIES_END -->

        <div class="timestamp">
            Last Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>
"""
            # Write the updated content
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"Updated bug history: {filename}")
            self.bug_report_count += active_bugs
            
        except Exception as e:
            print(f"Error generating bug report: {str(e)}")

    def detect_obstacle(self):
        player = self.game.player
        check_distance = 32  # Check 32 pixels ahead
        check_height = 32   # Check for obstacles up to 32 pixels high
        
        # Determine direction we're moving
        moving_right = self.game.movement[1]
        moving_left = self.game.movement[0]
        
        if not (moving_right or moving_left):
            return False, 0
            
        # Check for obstacle in movement direction
        check_x = player.pos[0] + (check_distance if moving_right else -check_distance)
        
        # First check at ground level
        ground_pos = (check_x, player.pos[1])
        if not self.game.tilemap.solid_check(ground_pos):
            return False, 0  # No obstacle if there's nothing at ground level
        
        # If there's something at ground level, check its height
        for height in range(0, check_height, 8):
            check_pos = (check_x, player.pos[1] + height)
            if not self.game.tilemap.solid_check(check_pos):
                if height > 0:  # Only consider it an obstacle if it has height
                    if self.debug:
                        print(f"Obstacle detected at height: {height}px")
                    return True, height
                return False, 0  # Not an obstacle if it's just a single pixel
                
        return True, check_height  # Full height obstacle

    def can_jump(self):
        current_time = pygame.time.get_ticks()
        player = self.game.player
        
        # Basic conditions for jumping
        cooldown_ok = current_time - self.last_jump_time > self.jump_cooldown
        attempts_ok = self.jump_attempts < self.max_jump_attempts
        
        # Must be on ground to jump
        if not player.collisions['down']:
            return False
        
        # Check if we're actually moving
        if not (self.game.movement[0] or self.game.movement[1]):
            return False
            
        return cooldown_ok and attempts_ok

    def try_jump(self, reason=""):
        current_time = pygame.time.get_ticks()
        player = self.game.player
        
        if self.can_jump():
            if self.debug:
                print(f"Jumping! Reason: {reason}")
            
            player.jump()
            self.last_jump_time = current_time
            self.jump_attempts += 1
            
            # Handle double jump usage
            if not player.collisions['down']:
                self.can_double_jump = False
            
            if self.debug:
                print(f"Jump attempt {self.jump_attempts}/{self.max_jump_attempts}")
            return True
            
        return False

    def try_periodic_jump(self):
        current_time = pygame.time.get_ticks()
        player = self.game.player
        
        # Check if it's time for periodic jump
        if current_time - self.last_periodic_jump >= self.periodic_jump_interval:
            if player.collisions['down']:  # Only jump if on ground
                if self.debug:
                    print("Performing periodic jump!")
                player.jump()
                self.last_periodic_jump = current_time
                return True
        return False

    def find_nearest_platform(self):
        player = self.game.player
        scan_range = self.platform_scan_range
        min_distance = float('inf')
        best_platform = None
        
        # Start from player's position
        start_x = player.pos[0] - scan_range
        end_x = player.pos[0] + scan_range
        start_y = player.pos[1]
        end_y = player.pos[1] + scan_range
        
        # Scan area below player in a grid
        for x in range(int(start_x), int(end_x), 16):  # 16-pixel steps for efficiency
            for y in range(int(start_y), int(end_y), 16):
                # Check if this position is a platform
                if self.game.tilemap.solid_check((x, y)):
                    # Check if there's empty space above this position (valid platform)
                    if not self.game.tilemap.solid_check((x, y - 16)):
                        # Calculate distance to this platform
                        dist_x = x - player.pos[0]
                        dist_y = y - player.pos[1]
                        distance = math.sqrt(dist_x**2 + dist_y**2)
                        
                        # Update if this is the nearest platform
                        if distance < min_distance:
                            min_distance = distance
                            best_platform = (x, y - 16)  # Store position above platform
                            
                            if self.debug:
                                print(f"Found platform at ({x}, {y}) - Distance: {distance:.1f}px")
        
        return best_platform, min_distance

    def should_double_jump(self):
        player = self.game.player
        
        # Only consider double jumping if:
        # 1. We're falling (not on ground)
        # 2. We have double jump available
        # 3. We've been falling for at least a short time
        if not player.collisions['down'] and self.can_double_jump:
            # Find nearest platform
            nearest_platform, distance = self.find_nearest_platform()
            
            if nearest_platform:
                if self.debug:
                    print(f"Nearest platform found at distance: {distance:.1f}px")
                
                # Calculate if platform is reachable with double jump
                platform_x, platform_y = nearest_platform
                height_diff = platform_y - player.pos[1]
                
                # Platform should be above us and within reasonable height
                if height_diff < 0 and abs(height_diff) < self.max_jump_height:
                    return True, nearest_platform
            
            elif self.debug:
                print("No suitable platform found for double jump")
        
        return False, None

    def try_double_jump(self, target_platform):
        current_time = pygame.time.get_ticks()
        player = self.game.player
        
        # Only double jump if we haven't recently jumped
        if current_time - self.last_jump_time > self.jump_cooldown:
            if self.debug:
                print(f"Double jumping towards platform at {target_platform}")
            
            player.jump()
            self.last_jump_time = current_time
            self.can_double_jump = False  # Use up double jump
            
            # Move towards platform horizontally
            if target_platform[0] > player.pos[0]:
                self.game.movement[1] = True  # Move right
            else:
                self.game.movement[0] = True  # Move left
            
            return True
        
        return False

    def update(self):
        current_time = pygame.time.get_ticks()
        player = self.game.player
        
        # Check for combat bugs (HIGH PRIORITY)
        self.detect_attack_bug()
        
        # Check for bullet survival bug (HIGH PRIORITY)
        self.detect_bullet_survival_bug()
        
        # Check for immortal fall bug (HIGHEST PRIORITY)
        self.detect_immortal_fall_bug()
        
        # Reset movement
        self.game.movement = [False, False]
        
        # Try periodic jump (HIGH PRIORITY)
        if self.try_periodic_jump():
            if self.debug:
                print("Executed periodic jump!")
        
        # Check if we need to double jump to safety
        if not player.collisions['down']:  # If we're in the air
            should_double, target_platform = self.should_double_jump()
            if should_double:
                if self.try_double_jump(target_platform):
                    if self.debug:
                        print("Executed double jump to reach platform!")
                    return  # Focus on reaching platform
        else:
            # Reset double jump when on ground
            self.can_double_jump = True
            self.last_ground_time = current_time
        
        # Handle dodging projectiles (HIGHEST PRIORITY)
        should_dodge, proj_dir, time_to_impact, same_level = self.should_dodge()
        if should_dodge:
            if self.debug:
                print("DODGE MODE ACTIVATED!")
            
            # If bullet is at same height, try to jump
            if same_level and player.collisions['down']:
                if self.try_jump("Bullet dodge"):
                    if self.debug:
                        print("Jumping to dodge bullet!")
            
            # Move away from projectile
            if proj_dir > 0:
                self.game.movement[0] = True  # Move left
            else:
                self.game.movement[1] = True  # Move right
            return  # Focus on dodging
        
        # Get nearest enemy and distance
        nearest_enemy, distance = self.get_nearest_enemy()
        
        # Attack nearest enemy (Secondary priority)
        if nearest_enemy:
            if self.debug:
                print(f"Targeting enemy at distance {distance}")
            dist_x = nearest_enemy.pos[0] - player.pos[0]
            dist_y = nearest_enemy.pos[1] - player.pos[1]
            
            # Set movement direction towards enemy
            if abs(dist_x) > 20:
                if dist_x > 0:
                    self.game.movement[1] = True  # Move right
                else:
                    self.game.movement[0] = True  # Move left
            
            # Check for obstacles in our path
            has_obstacle, obstacle_height = self.detect_obstacle()
            if has_obstacle and player.collisions['down']:
                if obstacle_height > 8:  # Only jump if obstacle is significant
                    if self.try_jump("Obstacle in path"):
                        if self.debug:
                            print(f"Jumping over obstacle of height: {obstacle_height}px")
        
        # Add remaining bug detection calls
        self.detect_decision_bug()
        
        # Generate report if any bugs are active
        if any(bug['active'] for bug in self.bugs_detected.values()):
            self.generate_bug_report()
            
        # Reset bug states after reporting
        for bug_type in self.bugs_detected:
            self.bugs_detected[bug_type]['active'] = False 