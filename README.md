# Pygame Platformer with AI Bug Detection System

A sophisticated 2D platformer game built with Pygame, featuring an advanced AI player and automated bug detection system. The project implements real-time monitoring and reporting of gameplay anomalies through an elegant HTML-based reporting system.

> This project builds upon and enhances the original [Pygame-Platformer by BoboStyx](https://github.com/BoboStyx/Pygame-Platformer) by adding advanced AI capabilities and automated bug detection features.

The Project with path finding ai without bugs is https://github.com/purushottamnar/AI-GAME-TEST-BOT/Pygame-Platformer-main.zip

## 🎮 Features

### AI Player System
- Intelligent enemy targeting and combat
- Advanced movement with double-jump capabilities
- Obstacle detection and avoidance
- Platform detection and navigation
- Projectile dodging system

### 🐛 Bug Detection System
The system monitors and detects four types of gameplay anomalies:

1. **Combat Bugs** (🗡️)
   - Detects combat inaction when enemies are in range
   - Monitors attack opportunities and engagement
   - Threshold: 4 seconds without attacking when enemies are within 100px

2. **Immortal Fall Bugs** (💀)
   - Tracks continuous falling without platforms
   - Monitors excessive jump attempts
   - Triggers after 15 seconds without platform detection
   - Scans 200px below player for platforms

3. **Decision Making Bugs** (🤔)
   - Monitors AI decision consistency
   - Detects rapid target switching
   - Triggers on more than 3 switches within 1 second

4. **Bullet Survival Bugs** (🎯)
   - Tracks bullet hit survival
   - Monitors damage threshold violations
   - Triggers after surviving 3+ hits

### 📊 Automated Bug Reporting
- Real-time HTML report generation
- Session-based bug tracking
- Persistent bug history
- Visual metrics and analytics
- Color-coded bug categorization

## 🚀 Getting Started

### Prerequisites
- Python 3.x
- Pygame library

### Installation
1. Clone the repository:
```bash
git clone https://github.com/yourusername/Pygame-Platformer.git
cd Pygame-Platformer
```

2. Install required dependencies:
```bash
pip install pygame
```

3. Run the game:
```bash
python Hpgame.py
```

### Controls
- **TAB**: Enable/Disable AI Player
- **Arrow Keys**: Manual Movement
- **SPACE**: Jump
- **Z**: Attack

## 📈 Bug Reports

Bug reports are automatically generated in the `Logs` directory as `gameplay_bug_history.html`. Each report includes:
- Session information
- Bug type and occurrence time
- Detailed metrics and analysis
- Visual representation of bug data

### Report Features
- **Session Tracking**: Each gameplay session is uniquely identified
- **Bug Categories**: Color-coded for easy identification
- **Metrics Dashboard**: Real-time statistics and counters
- **Persistent History**: Maintains record across multiple sessions

## 🔧 Technical Details

### AI Player Components
- Target acquisition and tracking
- Platform detection and navigation
- Combat engagement logic
- Obstacle avoidance system

### Bug Detection Parameters
- Combat inaction threshold: 4 seconds
- Fall detection range: 200 pixels
- Platform scan interval: 16 pixels
- Maximum jump attempts: 30

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🎯 Future Enhancements
- Additional bug detection types
- Machine learning-based anomaly detection
- Enhanced visualization of bug patterns
- Real-time bug analysis dashboard
- Network-based bug reporting

## 🔍 Debug Mode
Debug mode can be enabled by setting `self.debug = True` in the AIPlayer class, providing detailed console output for:
- Platform detection
- Combat engagement
- Movement decisions
- Bug detection events

Thanks for checking out this repository!

This is my 2d platformer using pygame to do such, credit to [Donal Salin](https://github.com/DonalSa) for help with the sprites, animation, sfx, and music.
The objective of the game is to eliminate all the enemies on the current level to load to the next level. There are a total of 3 levels.
You can choose between two characters.

Okarin:
![image](https://github.com/user-attachments/assets/f6e29327-cb55-4a52-83f7-5e07f6d9fc3e)

or Bobo:
![image](https://github.com/user-attachments/assets/57f6bbd4-9328-47a3-aa8f-2274135e053c)

Okarin has three jumps, while Bobo has two dashes.
The controls are W,A,S,D for movement, you can also use the arrow keys if you would like. X or Left Shift for dash.  W and Up Arrow Key are for jump.
The enemies shoot via guns and the player must dodge these projectiles and dash into the enemies to eliminate them.
If the player gets shot they restart the current level from the start with all the enemies reloaded in.
The player will also have to reload in if they are freefalling for too long, so navigate wisely!
Wall jumps use up the players jumps as well i.e. if playing Okarin and you jump onto a wall using one jump, jumping of the wall consumes a jump meaning you only have one jump left in the air.

Here is what should load when you run the game. (Depends on your character)
![image](https://github.com/user-attachments/assets/5b52d1b6-f4a4-4d7c-97e0-63fc1f38fb12)

To run this game go into the file Hpgame.py and run it. Pygame and python3 should be installed to run this game.

![image](https://github.com/user-attachments/assets/16364cfe-eff9-493d-9dc0-532a1a8261c0)

![image](https://github.com/user-attachments/assets/bb413956-17fc-4644-a123-f0b743f92c72)

Thank you for checking out my game and enjoy.

INTENDED FOR WINDOWS BASED SYSTEMS
