<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <span>SUSHI Hunter</span>
      <div>
        <span class="me-4">Level: {{ level }}</span>
        <span class="score">Score: {{ score }}</span>
      </div>
    </v-card-title>
    <v-card-subtitle>
      Help CELUS eat as much SUSHI as possible before the bugs get him!
    </v-card-subtitle>
    <v-card-text>
      <div class="game-container">
        <!-- Labyrinth -->
        <div
          v-for="(wall, index) in walls"
          :key="'wall-' + index"
          class="wall"
          :style="{
            left: `${wall.x}px`,
            top: `${wall.y}px`,
            width: `${wall.width}px`,
            height: `${wall.height}px`,
          }"
        ></div>

        <!-- Power-ups -->
        <div
          v-for="(powerUp, index) in powerUps"
          :key="'power-' + index"
          class="power-up"
          :style="{ left: `${powerUp.x}px`, top: `${powerUp.y}px` }"
          :class="{ eaten: powerUp.eaten, [powerUp.type]: true }"
        >
          <v-icon :icon="powerUp.icon" size="small"></v-icon>
        </div>

        <!-- Sushi items to collect -->
        <div
          v-for="(sushi, index) in sushiItems"
          :key="'sushi-' + index"
          class="sushi"
          :style="{ left: `${sushi.x}px`, top: `${sushi.y}px` }"
          :class="{ eaten: sushi.eaten }"
        >
          <img
            src="@/assets/game_sushi.png"
            alt="Sushi"
            :style="{
              transform: `rotate(${sushi.rotation}deg) scale(${sushi.scale})`,
            }"
          />
        </div>

        <!-- Enemy bugs -->
        <div
          v-for="(bug, index) in bugs"
          :key="'bug-' + index"
          class="bug"
          :style="{
            left: `${bug.x}px`,
            top: `${bug.y}px`,
            transform: `rotate(${bug.direction}deg)`,
            color: bug.color,
          }"
        >
          <v-icon :icon="bug.icon" size="small"></v-icon>
        </div>

        <!-- Player -->
        <div
          class="player"
          :style="{
            left: `${pacmanPosition.x}px`,
            top: `${pacmanPosition.y}px`,
            transform: `rotate(${pacmanDirection}deg)`,
          }"
          :class="{
            'game-over': gameOver,
            'player-invincible': playerInvincible,
            'player-flashing': playerFlashing,
          }"
        >
          <img src="@/assets/celus-C.png" alt="Player" />
        </div>

        <!-- Active power-up indicator -->
        <div v-if="activePowerUp" class="active-power-up">
          <v-icon :icon="activePowerUp.icon" size="small"></v-icon>
          <div class="power-up-progress">
            <div
              class="power-up-progress-bar"
              :style="{
                width: `${
                  (powerUpDuration / (activePowerUp.duration * 1000)) * 100
                }%`,
              }"
            ></div>
          </div>
        </div>

        <!-- Game over overlay -->
        <div v-if="gameOver" class="game-over-overlay">
          <div class="game-over-text">
            <h2>Game Over!</h2>
            <p>Score: {{ score }}</p>
            <v-btn color="primary" @click="restartGame">Play Again</v-btn>
          </div>
        </div>

        <!-- Win overlay -->
        <div v-if="gameWon" class="game-win-overlay">
          <div class="game-win-text">
            <h2>You Win!</h2>
            <p>Score: {{ score }}</p>
            <v-btn color="primary" @click="restartGame">Play Again</v-btn>
          </div>
        </div>

        <!-- Next Level Button -->
        <div v-if="showNextLevelButton" class="next-level-overlay">
          <div class="next-level-text">
            <h2>Level Complete!</h2>
            <p>Score: {{ score }}</p>
            <v-btn color="primary" @click="startNextLevel">Next Level</v-btn>
          </div>
        </div>

        <div class="game-instructions">
          <v-icon icon="fas fa-arrow-up"></v-icon>
          <v-icon icon="fas fa-arrow-down"></v-icon>
          <v-icon icon="fas fa-arrow-left"></v-icon>
          <v-icon icon="fas fa-arrow-right"></v-icon>
          to move
        </div>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn color="red" text @click="closePacmanGame">Close</v-btn>
    </v-card-actions>
  </v-card>
</template>

<script>
export default {
  name: "SushiLoaderGame",

  emits: ["close"],

  data() {
    return {
      pacmanPosition: { x: 0, y: 0 },
      pacmanDirection: 0,
      score: 0,
      bugs: [],
      pacmanMovementInterval: null,
      bugGenerationInterval: null,
      gameStartTime: null,
      gameHideTimeout: null,
      userControlActive: false,
      userControlTimeout: null,
      gameWidth: 650,
      gameHeight: 400,
      walls: [],
      sushiItems: [],
      gameOver: false,
      gameWon: false,
      powerUps: [],
      activePowerUp: null,
      powerUpDuration: null,
      powerUpInterval: null,
      sounds: {
        eat: null,
        powerUp: null,
        death: null,
        win: null,
      },
      level: 1,
      playerInvincible: false,
      playerSpeed: 3,
      playerFlashing: false,
      levels: [
        {
          name: "Level 1 - The Beginning",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },
            { x: 100, y: 50, width: 450, height: 20 },
            { x: 100, y: 230, width: 450, height: 20 },
            { x: 150, y: 150, width: 350, height: 20 },
            { x: 200, y: 100, width: 250, height: 20 },
          ],
          sushiCount: 30,
          powerUpCount: 1,
          bugCount: 4,
          bugTypes: ["random", "random", "chase", "patrol"],
        },
        {
          name: "Level 2 - The Corridor",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            // center box
            { x: 325, y: 150, width: 20, height: 100 },
            { x: 285, y: 190, width: 100, height: 20 },

            // top left corner
            { x: 50, y: 50, width: 80, height: 20 },
            { x: 50, y: 50, width: 20, height: 80 },

            // top right corner
            { x: 540, y: 50, width: 60, height: 20 },
            { x: 600, y: 50, width: 20, height: 80 },

            // bottom left corner
            { x: 50, y: 330, width: 80, height: 20 },
            { x: 50, y: 250, width: 20, height: 80 },

            // bottom right corner
            { x: 540, y: 330, width: 60, height: 20 },
            { x: 600, y: 270, width: 20, height: 80 },

            //t-cross-first
            { x: 285, y: 50, width: 100, height: 20 },
            { x: 325, y: 50, width: 20, height: 60 },

            //t-cross-second
            { x: 235, y: 50, width: 20, height: 100 },
            { x: 235, y: 100, width: 60, height: 20 },

            //t-cross-third
            { x: 415, y: 50, width: 20, height: 100 },
            { x: 375, y: 100, width: 60, height: 20 },

            //mirrored t-cross-first (bottom)
            { x: 285, y: 330, width: 100, height: 20 },
            { x: 325, y: 290, width: 20, height: 60 },

            //mirrored t-cross-second (bottom)
            { x: 235, y: 200, width: 20, height: 100 },
            { x: 235, y: 280, width: 60, height: 20 },

            //mirrored t-cross-third (bottom)
            { x: 415, y: 200, width: 20, height: 100 },
            { x: 375, y: 280, width: 60, height: 20 },
          ],
          sushiCount: 30,
          powerUpCount: 1,
          bugCount: 4,
          bugTypes: ["random", "random", "random", "chase"],
        },
        {
          name: "Level 3 - The Maze",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            // top left corner
            { x: 50, y: 50, width: 80, height: 20 },
            { x: 50, y: 50, width: 20, height: 80 },

            // top right corner
            { x: 540, y: 50, width: 60, height: 20 },
            { x: 600, y: 50, width: 20, height: 80 },

            // bottom left corner
            { x: 50, y: 330, width: 80, height: 20 },
            { x: 50, y: 250, width: 20, height: 80 },

            // bottom right corner
            { x: 540, y: 330, width: 60, height: 20 },
            { x: 600, y: 270, width: 20, height: 80 },

            //t-cross-first
            { x: 285, y: 50, width: 100, height: 20 },
            { x: 325, y: 50, width: 20, height: 110 },
            { x: 285, y: 145, width: 100, height: 20 },

            //t-cross-second
            { x: 225, y: 50, width: 20, height: 100 },
            { x: 225, y: 100, width: 60, height: 20 },

            //t-cross-third
            { x: 425, y: 50, width: 20, height: 100 },
            { x: 385, y: 100, width: 60, height: 20 },

            //mirrored t-cross-first (bottom)
            { x: 285, y: 330, width: 100, height: 20 },
            { x: 325, y: 290, width: 20, height: 60 },

            { x: 175, y: 160, width: 20, height: 190 },
            { x: 50, y: 160, width: 145, height: 20 },

            //mirrored t-cross-second (bottom)
            { x: 225, y: 200, width: 20, height: 100 },
            { x: 275, y: 200, width: 20, height: 100 },
            { x: 275, y: 200, width: 100, height: 20 },

            //mirrored t-cross-third (bottom)
            { x: 425, y: 200, width: 20, height: 100 },
            { x: 385, y: 280, width: 60, height: 20 },
            { x: 375, y: 200, width: 20, height: 50 },

            { x: 475, y: 50, width: 20, height: 170 },
            { x: 475, y: 220, width: 145, height: 20 },
          ],
          sushiCount: 30,
          powerUpCount: 2,
          bugCount: 5,
          bugTypes: ["random", "random", "random", "chase", "chase"],
        },
        {
          name: "Level 4 - The Crossroads",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            { x: 50, y: 330, width: 250, height: 20 },
            { x: 330, y: 330, width: 290, height: 20 },

            { x: 50, y: 50, width: 20, height: 100 },
            { x: 50, y: 190, width: 20, height: 110 },

            { x: 50, y: 50, width: 250, height: 20 },
            { x: 330, y: 50, width: 290, height: 20 },

            { x: 600, y: 50, width: 20, height: 100 },
            { x: 600, y: 190, width: 20, height: 110 },

            { x: 100, y: 280, width: 250, height: 20 },
            { x: 390, y: 280, width: 180, height: 20 },

            { x: 100, y: 100, width: 20, height: 100 },
            { x: 100, y: 240, width: 20, height: 60 },

            { x: 120, y: 100, width: 250, height: 20 },
            { x: 400, y: 100, width: 170, height: 20 },

            { x: 550, y: 100, width: 20, height: 100 },
            { x: 550, y: 240, width: 20, height: 60 },

            { x: 150, y: 230, width: 250, height: 20 },
            { x: 440, y: 230, width: 80, height: 20 },

            { x: 150, y: 150, width: 20, height: 50 },

            { x: 170, y: 150, width: 250, height: 20 },
            { x: 450, y: 150, width: 70, height: 20 },

            { x: 500, y: 150, width: 20, height: 50 },
          ],
          sushiCount: 30,
          powerUpCount: 2,
          bugCount: 6,
          bugTypes: [
            "random",
            "random",
            "random",
            "random",
            "random",
            "random",
          ],
        },
        {
          name: "Level 5 - The Fortress",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            { x: 50, y: 330, width: 50, height: 20 },
            { x: 130, y: 330, width: 50, height: 20 },
            { x: 210, y: 330, width: 50, height: 20 },
            { x: 290, y: 330, width: 50, height: 20 },
            { x: 370, y: 330, width: 50, height: 20 },
            { x: 450, y: 330, width: 50, height: 20 },
            { x: 530, y: 330, width: 90, height: 20 },

            { x: 50, y: 50, width: 20, height: 50 },
            { x: 50, y: 130, width: 20, height: 50 },
            { x: 50, y: 210, width: 20, height: 50 },
            { x: 50, y: 290, width: 20, height: 40 },

            { x: 50, y: 50, width: 50, height: 20 },
            { x: 130, y: 50, width: 50, height: 20 },
            { x: 210, y: 50, width: 50, height: 20 },
            { x: 290, y: 50, width: 50, height: 20 },
            { x: 370, y: 50, width: 50, height: 20 },
            { x: 450, y: 50, width: 50, height: 20 },
            { x: 530, y: 50, width: 90, height: 20 },

            { x: 600, y: 50, width: 20, height: 50 },
            { x: 600, y: 130, width: 20, height: 50 },
            { x: 600, y: 210, width: 20, height: 50 },
            { x: 600, y: 290, width: 20, height: 40 },

            { x: 100, y: 280, width: 50, height: 20 },
            { x: 180, y: 280, width: 50, height: 20 },
            { x: 260, y: 280, width: 50, height: 20 },
            { x: 340, y: 280, width: 50, height: 20 },
            { x: 420, y: 280, width: 50, height: 20 },
            { x: 500, y: 280, width: 50, height: 20 },

            { x: 100, y: 100, width: 20, height: 50 },
            { x: 100, y: 180, width: 20, height: 50 },
            { x: 100, y: 260, width: 20, height: 40 },

            { x: 100, y: 100, width: 50, height: 20 },
            { x: 180, y: 100, width: 50, height: 20 },
            { x: 260, y: 100, width: 50, height: 20 },
            { x: 340, y: 100, width: 50, height: 20 },
            { x: 420, y: 100, width: 50, height: 20 },
            { x: 500, y: 100, width: 50, height: 20 },

            { x: 550, y: 100, width: 20, height: 50 },
            { x: 550, y: 180, width: 20, height: 50 },
            { x: 550, y: 260, width: 20, height: 40 },

            { x: 150, y: 230, width: 70, height: 20 },
            { x: 250, y: 230, width: 50, height: 20 },
            { x: 330, y: 230, width: 50, height: 20 },
            { x: 410, y: 230, width: 50, height: 20 },
            { x: 490, y: 230, width: 30, height: 20 },

            { x: 150, y: 150, width: 70, height: 20 },
            { x: 250, y: 150, width: 50, height: 20 },
            { x: 330, y: 150, width: 50, height: 20 },
            { x: 410, y: 150, width: 50, height: 20 },

            { x: 500, y: 150, width: 20, height: 50 },
          ],
          sushiCount: 30,
          powerUpCount: 2,
          bugCount: 6,
          bugTypes: ["random", "random", "random", "random", "random", "chase"],
        },
        {
          name: "Level 6 - The Labyrinth",
          walls: [
            // Borders
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },
            { x: 50, y: 330, width: 50, height: 20 },
            { x: 130, y: 330, width: 50, height: 20 },
            { x: 210, y: 330, width: 50, height: 20 },
            { x: 290, y: 330, width: 50, height: 20 },
            { x: 370, y: 330, width: 50, height: 20 },
            { x: 450, y: 330, width: 50, height: 20 },
            { x: 530, y: 330, width: 90, height: 20 },

            { x: 50, y: 280, width: 50, height: 20 },
            { x: 130, y: 280, width: 50, height: 20 },
            { x: 210, y: 280, width: 50, height: 20 },
            { x: 290, y: 280, width: 50, height: 20 },
            { x: 370, y: 280, width: 50, height: 20 },
            { x: 450, y: 280, width: 50, height: 20 },
            { x: 530, y: 280, width: 90, height: 20 },

            { x: 50, y: 230, width: 50, height: 20 },
            { x: 130, y: 230, width: 50, height: 20 },
            { x: 210, y: 230, width: 50, height: 20 },
            { x: 290, y: 230, width: 50, height: 20 },
            { x: 370, y: 230, width: 50, height: 20 },
            { x: 450, y: 230, width: 50, height: 20 },
            { x: 530, y: 230, width: 90, height: 20 },

            { x: 50, y: 180, width: 50, height: 20 },
            { x: 130, y: 180, width: 50, height: 20 },
            { x: 210, y: 180, width: 50, height: 20 },
            { x: 290, y: 180, width: 50, height: 20 },
            { x: 370, y: 180, width: 50, height: 20 },
            { x: 450, y: 180, width: 50, height: 20 },
            { x: 530, y: 180, width: 90, height: 20 },

            { x: 50, y: 130, width: 50, height: 20 },
            { x: 130, y: 130, width: 50, height: 20 },
            { x: 210, y: 130, width: 50, height: 20 },
            { x: 290, y: 130, width: 50, height: 20 },
            { x: 370, y: 130, width: 50, height: 20 },
            { x: 450, y: 130, width: 50, height: 20 },
            { x: 530, y: 130, width: 90, height: 20 },

            { x: 50, y: 80, width: 50, height: 20 },
            { x: 130, y: 80, width: 50, height: 20 },
            { x: 210, y: 80, width: 50, height: 20 },
            { x: 290, y: 80, width: 50, height: 20 },
            { x: 370, y: 80, width: 50, height: 20 },
            { x: 450, y: 80, width: 50, height: 20 },
            { x: 530, y: 80, width: 90, height: 20 },
          ],
          sushiCount: 20,
          powerUpCount: 3,
          bugCount: 7,
          bugTypes: [
            "random",
            "random",
            "random",
            "random",
            "random",
            "random",
            "random",
          ],
        },
        {
          name: "Level 7 - The Gauntlet",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            // top left corner
            { x: 50, y: 80, width: 140, height: 20 },
            { x: 50, y: 50, width: 20, height: 80 },

            // top right corner
            { x: 530, y: 80, width: 70, height: 20 },
            { x: 600, y: 50, width: 20, height: 140 },
            { x: 530, y: 50, width: 20, height: 140 },

            // bottom left corner
            { x: 50, y: 300, width: 90, height: 20 },
            { x: 50, y: 270, width: 20, height: 80 },

            // bottom right corner
            { x: 475, y: 300, width: 125, height: 20 },
            { x: 600, y: 270, width: 20, height: 80 },

            //t-cross-first
            { x: 285, y: 50, width: 100, height: 20 },
            { x: 325, y: 50, width: 20, height: 110 },
            { x: 285, y: 145, width: 100, height: 20 },

            //t-cross-second
            { x: 225, y: 50, width: 20, height: 100 },
            { x: 225, y: 100, width: 60, height: 20 },

            //t-cross-third
            { x: 425, y: 50, width: 20, height: 100 },
            { x: 385, y: 100, width: 60, height: 20 },

            //mirrored t-cross-first (bottom)
            { x: 285, y: 330, width: 100, height: 20 },
            { x: 325, y: 250, width: 20, height: 80 },

            { x: 175, y: 160, width: 20, height: 190 },
            { x: 50, y: 160, width: 145, height: 20 },

            //mirrored t-cross-second (bottom)
            { x: 225, y: 200, width: 20, height: 150 },
            { x: 275, y: 200, width: 20, height: 100 },
            { x: 275, y: 200, width: 100, height: 20 },

            //mirrored t-cross-third (bottom)
            { x: 425, y: 200, width: 20, height: 150 },
            { x: 385, y: 280, width: 60, height: 20 },
            { x: 375, y: 200, width: 20, height: 50 },

            { x: 475, y: 50, width: 20, height: 170 },
            { x: 475, y: 220, width: 145, height: 20 },
          ],
          sushiCount: 22,
          powerUpCount: 3,
          bugCount: 5,
          bugTypes: ["chase", "chase", "patrol", "random", "patrol"],
        },
        {
          name: "Level 8 - The Challenge",
          walls: [
            { x: 0, y: 0, width: 650, height: 20 },
            { x: 0, y: 0, width: 20, height: 400 },
            { x: 0, y: 380, width: 650, height: 20 },
            { x: 650, y: 0, width: 20, height: 400 },

            { x: 50, y: 50, width: 20, height: 50 },
            { x: 50, y: 130, width: 20, height: 50 },
            { x: 50, y: 210, width: 20, height: 50 },
            { x: 50, y: 290, width: 20, height: 60 },

            { x: 100, y: 50, width: 20, height: 50 },
            { x: 100, y: 130, width: 20, height: 50 },
            { x: 100, y: 210, width: 20, height: 50 },
            { x: 100, y: 290, width: 20, height: 60 },

            { x: 150, y: 50, width: 20, height: 50 },
            { x: 150, y: 130, width: 20, height: 50 },
            { x: 150, y: 210, width: 20, height: 50 },
            { x: 150, y: 290, width: 20, height: 60 },

            { x: 200, y: 50, width: 20, height: 50 },
            { x: 200, y: 130, width: 20, height: 50 },
            { x: 200, y: 210, width: 20, height: 50 },
            { x: 200, y: 290, width: 20, height: 60 },

            { x: 250, y: 50, width: 20, height: 50 },
            { x: 250, y: 130, width: 20, height: 50 },
            { x: 250, y: 210, width: 20, height: 50 },
            { x: 250, y: 290, width: 20, height: 60 },

            { x: 300, y: 50, width: 20, height: 50 },
            { x: 300, y: 130, width: 20, height: 50 },
            { x: 300, y: 210, width: 20, height: 50 },
            { x: 300, y: 290, width: 20, height: 60 },

            { x: 350, y: 50, width: 20, height: 50 },
            { x: 350, y: 130, width: 20, height: 50 },
            { x: 350, y: 210, width: 20, height: 50 },
            { x: 350, y: 290, width: 20, height: 60 },

            { x: 400, y: 50, width: 20, height: 50 },
            { x: 400, y: 130, width: 20, height: 50 },
            { x: 400, y: 210, width: 20, height: 50 },
            { x: 400, y: 290, width: 20, height: 60 },

            { x: 450, y: 50, width: 20, height: 50 },
            { x: 450, y: 130, width: 20, height: 50 },
            { x: 450, y: 210, width: 20, height: 50 },
            { x: 450, y: 290, width: 20, height: 60 },

            { x: 500, y: 50, width: 20, height: 50 },
            { x: 500, y: 130, width: 20, height: 50 },
            { x: 500, y: 210, width: 20, height: 50 },
            { x: 500, y: 290, width: 20, height: 60 },

            { x: 550, y: 50, width: 20, height: 50 },
            { x: 550, y: 130, width: 20, height: 50 },
            { x: 550, y: 210, width: 20, height: 50 },
            { x: 550, y: 290, width: 20, height: 60 },

            { x: 600, y: 50, width: 20, height: 50 },
            { x: 600, y: 130, width: 20, height: 50 },
            { x: 600, y: 210, width: 20, height: 50 },
            { x: 600, y: 290, width: 20, height: 60 },
          ],
          sushiCount: 24,
          powerUpCount: 3,
          bugCount: 8,
          bugTypes: [
            "random",
            "random",
            "random",
            "random",
            "random",
            "random",
            "random",
            "chase",
          ],
        },
      ],
      showNextLevelButton: false,
    };
  },

  methods: {
    initPacmanGame() {
      // Reset level to 1 when starting a new game
      this.level = 1;

      // Adjust game area size for dialog
      this.gameWidth = 650;
      this.gameHeight = 400;

      // Reset game state
      this.gameOver = false;
      this.gameWon = false;
      this.score = 0;

      // Reset power-up state
      this.activePowerUp = null;
      this.powerUpDuration = null;
      if (this.powerUpInterval) clearInterval(this.powerUpInterval);
      this.playerInvincible = false;
      this.playerSpeed = 3;
      this.playerFlashing = false;

      // Create labyrinth walls
      this.createLabyrinth();

      // Clear any existing intervals
      if (this.pacmanMovementInterval)
        clearInterval(this.pacmanMovementInterval);
      if (this.bugGenerationInterval) clearInterval(this.bugGenerationInterval);

      // Set up game intervals
      this.pacmanMovementInterval = setInterval(
        () => this.updatePacmanPosition(),
        50,
      );
      this.bugGenerationInterval = setInterval(() => this.updateBugs(), 100);

      // Set the game start time
      this.gameStartTime = Date.now();
    },

    createPowerUps(count) {
      this.powerUps = [];

      // Define power-up types
      const powerUpTypes = [
        {
          type: "speed",
          icon: "fas fa-bolt",
          duration: 10, // seconds
          effect: () => {
            this.playerSpeed = 6; // Double speed
            // Play power-up sound if available
            if (this.sounds.powerUp) this.sounds.powerUp.play();
          },
          cleanup: () => {
            this.playerSpeed = 3; // Reset speed
          },
        },
        {
          type: "invincibility",
          icon: "fas fa-shield-alt",
          duration: 8, // seconds
          effect: () => {
            this.playerInvincible = true;
            this.playerFlashing = true;
            // Play power-up sound if available
            if (this.sounds.powerUp) this.sounds.powerUp.play();
          },
          cleanup: () => {
            this.playerInvincible = false;
            this.playerFlashing = false;
          },
        },
        {
          type: "clear",
          icon: "fas fa-skull",
          duration: 5, // seconds
          effect: () => {
            // Make all bugs vulnerable and slow them down
            this.bugs.forEach((bug) => {
              bug.vulnerable = true;
              bug.originalSpeed = bug.speed;
              bug.speed = bug.speed * 0.5;
              bug.originalColor = bug.color;
              bug.color = "#3333aa"; // Change color to indicate vulnerability
            });
            // Play power-up sound if available
            if (this.sounds.powerUp) this.sounds.powerUp.play();
          },
          cleanup: () => {
            // Restore bugs' normal state
            this.bugs.forEach((bug) => {
              bug.vulnerable = false;
              if (bug.originalSpeed) bug.speed = bug.originalSpeed;
              bug.color = bug.originalColor || bug.color;
            });
          },
        },
      ];

      // Try to place power-ups in valid positions
      for (let i = 0; i < count; i++) {
        const position = this.findValidPosition(30, 30);

        // Select a random power-up type
        const powerUpType =
          powerUpTypes[Math.floor(Math.random() * powerUpTypes.length)];

        this.powerUps.push({
          x: position.x,
          y: position.y,
          type: powerUpType.type,
          icon: powerUpType.icon,
          duration: powerUpType.duration,
          effect: powerUpType.effect,
          cleanup: powerUpType.cleanup,
          eaten: false,
        });
      }
    },

    createLabyrinth() {
      // Get current level configuration
      const levelConfig = this.levels[this.level - 1] || this.levels[0];

      // Set walls from level configuration
      this.walls = levelConfig.walls;

      // Create sushi items
      this.createSushiItems(levelConfig.sushiCount);

      // Create power-ups
      this.createPowerUps(levelConfig.powerUpCount);

      // Create bugs with specified types
      this.createBugs(levelConfig.bugCount, levelConfig.bugTypes);

      // Set player starting position
      this.pacmanPosition = this.findValidPosition(30, 30, this.bugs, 150); // Player size, bugs array, min distance 150px
    },

    findValidPosition(
      objectWidth,
      objectHeight,
      entitiesToAvoid = [],
      minAvoidDistance = 0,
    ) {
      let attempts = 0;
      let position;
      let tooCloseToEntity = false;

      do {
        tooCloseToEntity = false; // Reset for each attempt
        position = {
          x:
            Math.floor(Math.random() * (this.gameWidth - objectWidth - 20)) +
            10,
          y:
            Math.floor(Math.random() * (this.gameHeight - objectHeight - 20)) +
            10,
        };

        if (entitiesToAvoid.length > 0 && minAvoidDistance > 0) {
          const objectCenterX = position.x + objectWidth / 2;
          const objectCenterY = position.y + objectHeight / 2;
          for (const entity of entitiesToAvoid) {
            // Assuming entities (bugs) are also roughly 30x30 for this check, their center is x+15, y+15
            const entityCenterX = entity.x + 15;
            const entityCenterY = entity.y + 15;
            const dx = objectCenterX - entityCenterX;
            const dy = objectCenterY - entityCenterY;
            if (Math.sqrt(dx * dx + dy * dy) < minAvoidDistance) {
              tooCloseToEntity = true;
              break;
            }
          }
        }

        attempts++;
      } while (
        (this.checkWallCollision(position, objectWidth, objectHeight) ||
          tooCloseToEntity) &&
        attempts < 100
      );

      if (attempts >= 100 && tooCloseToEntity) {
        console.warn(
          "Could not find a spawn position sufficiently far from all entities after 100 attempts. Player may spawn close to an enemy.",
        );
      }

      return position;
    },

    createSushiItems(count) {
      this.sushiItems = [];
      const minSushiDistance = 40; // Minimum center-to-center distance between sushi

      // Define sushi types with different point values and visual properties
      const sushiTypes = [
        { scale: 1.0, rotation: 0, points: 10 },
        { scale: 0.8, rotation: 45, points: 5 },
        { scale: 1.2, rotation: -45, points: 15 },
      ];

      // Grid-based placement to ensure good distribution
      const gridSize = 50; // Smaller grid size for more precise placement
      const gridWidth = Math.floor(this.gameWidth / gridSize);
      const gridHeight = Math.floor(this.gameHeight / gridSize);

      // Create a grid of possible positions
      const positions = [];
      for (let y = 0; y < gridHeight; y++) {
        for (let x = 0; x < gridWidth; x++) {
          positions.push({
            x: x * gridSize + gridSize / 2,
            y: y * gridSize + gridSize / 2,
          });
        }
      }

      // Shuffle the positions to randomize placement
      for (let i = positions.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [positions[i], positions[j]] = [positions[j], positions[i]];
      }

      // Try positions in order until we have enough valid ones
      let sushiCount = 0;
      for (let i = 0; i < positions.length && sushiCount < count; i++) {
        const candidateCenterPosition = positions[i]; // This is a pre-calculated center of a grid cell

        // Check with a larger margin around sushi to ensure it's accessible
        // Use a smaller size for checking wall collision to ensure there's space around the sushi
        const testTopLeftPosition = {
          x: candidateCenterPosition.x - 20, // Assuming 40x40 space for collision check
          y: candidateCenterPosition.y - 20,
        };

        if (!this.checkWallCollision(testTopLeftPosition, 40, 40)) {
          let tooCloseToOtherSushi = false;
          for (const existingSushi of this.sushiItems) {
            const existingSushiCenterX = existingSushi.x + 15;
            const existingSushiCenterY = existingSushi.y + 15;
            const dx = candidateCenterPosition.x - existingSushiCenterX;
            const dy = candidateCenterPosition.y - existingSushiCenterY;
            if (Math.sqrt(dx * dx + dy * dy) < minSushiDistance) {
              tooCloseToOtherSushi = true;
              break;
            }
          }

          if (!tooCloseToOtherSushi) {
            const sushiType =
              sushiTypes[Math.floor(Math.random() * sushiTypes.length)];
            this.sushiItems.push({
              x: candidateCenterPosition.x - 15, // Convert center to top-left for 30x30 sushi
              y: candidateCenterPosition.y - 15,
              eaten: false,
              scale: sushiType.scale,
              rotation: sushiType.rotation,
              points: sushiType.points,
            });
            sushiCount++;
          }
        }
      }

      // If we couldn't find enough valid positions, keep trying with more relaxed constraints
      if (sushiCount < count) {
        const remaining = count - sushiCount;
        for (let i = 0; i < remaining; i++) {
          // Create a specific findFoodPosition method to ensure food is accessible
          const position = this.findFoodPosition(
            this.sushiItems,
            minSushiDistance,
          ); // Pass existing items and distance
          if (position) {
            const sushiType =
              sushiTypes[Math.floor(Math.random() * sushiTypes.length)];
            this.sushiItems.push({
              x: position.x, // findFoodPosition returns top-left
              y: position.y,
              eaten: false,
              scale: sushiType.scale,
              rotation: sushiType.rotation,
              points: sushiType.points,
            });
            sushiCount++;
          } else {
            console.warn(
              "Could not place all sushi items with sufficient spacing in fallback.",
            );
            break; // Stop trying if no valid spot can be found
          }
        }
      }
    },

    // Special method to find positions specifically suitable for food items
    findFoodPosition(existingSushiItems = [], minDistanceToExisting = 0) {
      let attempts = 0;
      let candidateTopLeftPosition;
      let bestPosition = null;
      let bestWallDistance = 0;

      // Try multiple positions and find the one with the most open space
      while (attempts < 50) {
        // Increased attempts slightly
        candidateTopLeftPosition = {
          x: Math.floor(Math.random() * (this.gameWidth - 50)) + 25, // -50 allows for 30x30 item + 10 margin on each side
          y: Math.floor(Math.random() * (this.gameHeight - 50)) + 25,
        };

        // If not colliding with a wall
        if (!this.checkWallCollision(candidateTopLeftPosition, 30, 30)) {
          let tooCloseToOtherSushi = false;
          if (minDistanceToExisting > 0 && existingSushiItems.length > 0) {
            const newSushiCenterX = candidateTopLeftPosition.x + 15;
            const newSushiCenterY = candidateTopLeftPosition.y + 15;
            for (const item of existingSushiItems) {
              const existingSushiCenterX = item.x + 15;
              const existingSushiCenterY = item.y + 15;
              const dx = newSushiCenterX - existingSushiCenterX;
              const dy = newSushiCenterY - existingSushiCenterY;
              if (Math.sqrt(dx * dx + dy * dy) < minDistanceToExisting) {
                tooCloseToOtherSushi = true;
                break;
              }
            }
          }

          if (tooCloseToOtherSushi) {
            attempts++;
            continue; // Try another random spot
          }

          // Calculate distance to nearest wall (space around item)
          let currentWallDistance = this.calculateDistanceToNearestWall(
            candidateTopLeftPosition,
          );

          // Keep track of position with most space around it from walls
          if (currentWallDistance > bestWallDistance) {
            bestWallDistance = currentWallDistance;
            bestPosition = { ...candidateTopLeftPosition };
          }

          // If we found a position with good space from walls and other sushi, use it immediately
          if (currentWallDistance > 20) {
            // 20 is an arbitrary "good space" value from walls
            return candidateTopLeftPosition;
          }
        }
        attempts++;
      }

      // Return best position found or null if none suitable after all attempts
      return bestPosition;
    },

    // Calculate the distance to the nearest wall
    calculateDistanceToNearestWall(position) {
      let minDistance = 1000; // Large initial value

      for (const wall of this.walls) {
        // Calculate closest point on wall to the position
        const closestX = Math.max(
          wall.x,
          Math.min(position.x, wall.x + wall.width),
        );
        const closestY = Math.max(
          wall.y,
          Math.min(position.y, wall.y + wall.height),
        );

        // Calculate distance to this closest point
        const dx = position.x - closestX;
        const dy = position.y - closestY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Update minimum distance
        minDistance = Math.min(minDistance, distance);
      }

      return minDistance;
    },

    createBugs(count, bugTypes) {
      this.bugs = [];

      // Define bug types with different behaviors
      const bugDefinitions = {
        chase: {
          icon: "fas fa-spider",
          speed: 1.8,
          behavior: "chase",
          color: "#ff4444",
        },
        patrol: {
          icon: "fas fa-bug",
          speed: 1.2,
          behavior: "patrol",
          color: "#ff9900",
        },
        random: {
          icon: "fas fa-virus",
          speed: 2.2,
          behavior: "random",
          color: "#cc00cc",
        },
      };

      // Ensure bugTypes is an array and has enough elements
      const validBugTypes = Array.isArray(bugTypes) ? bugTypes : [];

      for (let i = 0; i < count; i++) {
        const position = this.findValidPosition(30, 30);
        // Get bug type from array or default to patrol if not available
        const bugTypeName = validBugTypes[i] || "patrol";
        const bugType = bugDefinitions[bugTypeName] || bugDefinitions.patrol;

        this.bugs.push({
          x: position.x,
          y: position.y,
          direction: Math.floor(Math.random() * 4) * 90,
          speed: bugType.speed + Math.random() * 0.5 - 0.25,
          behavior: bugType.behavior,
          icon: bugType.icon,
          color: bugType.color,
          patrolDistance: 0,
          patrolMax: 50 + Math.floor(Math.random() * 100),
          lastMove: Date.now(),
        });
      }
    },

    updatePacmanPosition() {
      if (this.gameOver || this.gameWon) return;

      const speed = this.playerSpeed; // Use the dynamic player speed
      let newPosition = { ...this.pacmanPosition };

      // Try moving in the desired direction
      if (this.pacmanDirection === 0) {
        // right
        newPosition.x += speed;
      } else if (this.pacmanDirection === 180) {
        // left
        newPosition.x -= speed;
      } else if (this.pacmanDirection === 270) {
        // up
        newPosition.y -= speed;
      } else if (this.pacmanDirection === 90) {
        // down
        newPosition.y += speed;
      }

      // Check wall collision
      if (!this.checkWallCollision(newPosition, 30, 30)) {
        this.pacmanPosition = newPosition;
      } else {
        // Try to slide along walls when hitting them at angles with improved sliding
        let slidePosition = { ...this.pacmanPosition };

        // Try more incremental sliding for smoother corner navigation
        if (this.pacmanDirection === 0 || this.pacmanDirection === 180) {
          // We're moving horizontally but hit a wall, try to slide vertically

          // Try sliding up with progressively smaller steps
          for (let step = speed / 2; step >= 1; step--) {
            slidePosition = { ...this.pacmanPosition };
            slidePosition.y -= step;
            if (
              !this.checkWallCollision(
                { ...slidePosition, x: newPosition.x },
                30,
                30,
              )
            ) {
              this.pacmanPosition = { ...slidePosition, x: newPosition.x };
              return;
            }
          }

          // Try sliding down with progressively smaller steps
          for (let step = speed / 2; step >= 1; step--) {
            slidePosition = { ...this.pacmanPosition };
            slidePosition.y += step;
            if (
              !this.checkWallCollision(
                { ...slidePosition, x: newPosition.x },
                30,
                30,
              )
            ) {
              this.pacmanPosition = { ...slidePosition, x: newPosition.x };
              return;
            }
          }
        } else {
          // We're moving vertically but hit a wall, try to slide horizontally

          // Try sliding left with progressively smaller steps
          for (let step = speed / 2; step >= 1; step--) {
            slidePosition = { ...this.pacmanPosition };
            slidePosition.x -= step;
            if (
              !this.checkWallCollision(
                { ...slidePosition, y: newPosition.y },
                30,
                30,
              )
            ) {
              this.pacmanPosition = { ...slidePosition, y: newPosition.y };
              return;
            }
          }

          // Try sliding right with progressively smaller steps
          for (let step = speed / 2; step >= 1; step--) {
            slidePosition = { ...this.pacmanPosition };
            slidePosition.x += step;
            if (
              !this.checkWallCollision(
                { ...slidePosition, y: newPosition.y },
                30,
                30,
              )
            ) {
              this.pacmanPosition = { ...slidePosition, y: newPosition.y };
              return;
            }
          }
        }

        // If no sliding worked, try diagonal movement as a last resort
        for (let step = speed / 3; step >= 1; step--) {
          // Try all four diagonal directions
          const diagonals = [
            { x: step, y: step },
            { x: step, y: -step },
            { x: -step, y: step },
            { x: -step, y: -step },
          ];

          for (const diagonal of diagonals) {
            slidePosition = {
              x: this.pacmanPosition.x + diagonal.x,
              y: this.pacmanPosition.y + diagonal.y,
            };

            if (!this.checkWallCollision(slidePosition, 30, 30)) {
              this.pacmanPosition = slidePosition;
              return;
            }
          }
        }
      }

      // Check sushi collision
      this.checkSushiCollision();

      // Check power-up collision
      this.checkPowerUpCollision();

      // Check bug collision
      this.checkBugCollision();

      // Check if all sushi collected
      this.checkWinCondition();
    },

    checkWallCollision(position, width, height) {
      // Add a small buffer to allow squeezing through tight corridors
      const buffer = 2;
      const playerRect = {
        left: position.x + buffer,
        right: position.x + width - buffer,
        top: position.y + buffer,
        bottom: position.y + height - buffer,
      };

      // Add support for smaller hit detection on walls for smoother movement
      for (const wall of this.walls) {
        // Adjust wall hitbox to be slightly smaller for easier navigation
        const wallBuffer = 1;
        const wallRect = {
          left: wall.x + wallBuffer,
          right: wall.x + wall.width - wallBuffer,
          top: wall.y + wallBuffer,
          bottom: wall.y + wall.height - wallBuffer,
        };

        if (
          playerRect.left < wallRect.right &&
          playerRect.right > wallRect.left &&
          playerRect.top < wallRect.bottom &&
          playerRect.bottom > wallRect.top
        ) {
          return true; // Collision detected
        }
      }

      return false; // No collision
    },

    checkSushiCollision() {
      const playerRadius = 15; // Half of player width/height

      this.sushiItems.forEach((sushi, index) => {
        if (!sushi.eaten) {
          const dx = this.pacmanPosition.x + playerRadius - (sushi.x + 15);
          const dy = this.pacmanPosition.y + playerRadius - (sushi.y + 15);
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < playerRadius + 10) {
            // Mark sushi as eaten
            this.sushiItems[index].eaten = true;
            // Add points based on sushi type
            this.score += sushi.points || 10; // Default to 10 if not specified

            // Play sound effect (optional)
            // this.playSound('eat');
          }
        }
      });
    },

    checkPowerUpCollision() {
      const playerRadius = 15; // Half of player width/height

      this.powerUps.forEach((powerUp, index) => {
        if (!powerUp.eaten) {
          const dx = this.pacmanPosition.x + playerRadius - (powerUp.x + 15);
          const dy = this.pacmanPosition.y + playerRadius - (powerUp.y + 15);
          const distance = Math.sqrt(dx * dx + dy * dy);

          if (distance < playerRadius + 15) {
            // Mark power-up as eaten
            this.powerUps[index].eaten = true;

            // End previous power-up if active
            if (this.activePowerUp && this.activePowerUp.cleanup) {
              this.activePowerUp.cleanup();
            }

            // Activate new power-up
            this.activePowerUp = powerUp;
            this.powerUpDuration = powerUp.duration * 1000;

            // Apply power-up effect
            if (powerUp.effect) {
              powerUp.effect();
            }

            // Set up countdown timer
            if (this.powerUpInterval) clearInterval(this.powerUpInterval);
            this.powerUpInterval = setInterval(() => {
              this.powerUpDuration -= 100;

              // End power-up when duration is over
              if (this.powerUpDuration <= 0) {
                clearInterval(this.powerUpInterval);
                if (this.activePowerUp && this.activePowerUp.cleanup) {
                  this.activePowerUp.cleanup();
                }
                this.activePowerUp = null;
              }
            }, 100);

            // Add bonus points
            this.score += 25;
          }
        }
      });
    },

    checkBugCollision() {
      const playerRadius = 15; // Half of player width/height

      this.bugs.forEach((bug) => {
        const dx = this.pacmanPosition.x + playerRadius - (bug.x + 15);
        const dy = this.pacmanPosition.y + playerRadius - (bug.y + 15);
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance < playerRadius + 10) {
          if (bug.vulnerable) {
            bug.x = -100; // Move it off-screen (effectively removing it)
            bug.y = -100;
            this.score += 50; // Bonus points for eating a bug
            // Game does not end, bug is eaten.
          } else if (this.playerInvincible) {
            // Bug is NOT vulnerable, BUT player IS invincible.over.
          } else {
            // Bug is NOT vulnerable, AND player is NOT invincible.
            this.gameOver = true;
            this.stopPacmanGame();
          }
        }
      });
    },

    updateBugs() {
      if (this.gameOver || this.gameWon) return;

      this.bugs.forEach((bug, index) => {
        // Calculate time since last move for smooth animation regardless of frame rate
        const now = Date.now();
        const deltaTime = now - bug.lastMove;
        const moveSpeed = (bug.speed * deltaTime) / 50; // Normalize by expected frame time

        // Store original position for collision check
        const originalPosition = { x: bug.x, y: bug.y };
        let newPosition = { ...bug };
        let newDirection = bug.direction;

        // Different behavior based on bug type
        switch (bug.behavior) {
          case "chase":
            // Chase the player directly
            const dx = this.pacmanPosition.x - bug.x;
            const dy = this.pacmanPosition.y - bug.y;

            // Determine direction based on player position
            if (Math.abs(dx) > Math.abs(dy)) {
              newDirection = dx > 0 ? 0 : 180; // right or left
            } else {
              newDirection = dy > 0 ? 90 : 270; // down or up
            }

            // Small chance to take a wrong turn (makes it less predictable)
            if (Math.random() < 0.05) {
              newDirection =
                (newDirection + (Math.random() < 0.5 ? 90 : 270)) % 360;
            }
            break;

          case "patrol":
            // Continue in the same direction until hitting obstacle or patrol limit
            if (bug.patrolDistance > bug.patrolMax) {
              // Change direction when patrol limit is reached
              newDirection = (bug.direction + 180) % 360; // Turn around
              bug.patrolDistance = 0;
            }
            break;

          case "random":
            // Move randomly
            if (Math.random() < 0.1) {
              const directions = [0, 90, 180, 270];
              newDirection = directions[Math.floor(Math.random() * 4)];
            }
            break;
        }

        // Calculate new position based on direction
        if (newDirection === 0) {
          // right
          newPosition.x += moveSpeed;
        } else if (newDirection === 180) {
          // left
          newPosition.x -= moveSpeed;
        } else if (newDirection === 270) {
          // up
          newPosition.y -= moveSpeed;
        } else if (newDirection === 90) {
          // down
          newPosition.y += moveSpeed;
        }

        // Update direction
        bug.direction = newDirection;

        // Check wall collision and update position if no collision
        if (!this.checkWallCollision(newPosition, 24, 24)) {
          // Update position
          this.bugs[index] = {
            ...newPosition,
            patrolDistance:
              bug.behavior === "patrol"
                ? bug.patrolDistance + moveSpeed
                : bug.patrolDistance,
          };
        } else {
          // If colliding with wall
          if (bug.behavior === "patrol") {
            // Patrol bug: reverse direction
            bug.direction = (bug.direction + 180) % 360;
            bug.patrolDistance = 0;
          } else {
            // Other bugs: pick a new random direction
            const possibleDirections = [0, 90, 180, 270].filter(
              (d) => d !== bug.direction,
            );
            bug.direction =
              possibleDirections[
                Math.floor(Math.random() * possibleDirections.length)
              ];
          }
        }

        // Update the timestamp of last move
        this.bugs[index].lastMove = now;
      });
    },

    checkWinCondition() {
      // Win condition: All sushi eaten
      if (
        this.sushiItems.length > 0 &&
        !this.sushiItems.some((sushi) => !sushi.eaten)
      ) {
        // If we're on the last level (10), show game won screen
        if (this.level >= 10) {
          this.gameWon = true;
          this.stopPacmanGame();
        } else {
          // Show next level button instead of auto-progressing
          this.showNextLevelButton = true;
          // Pause the game
          if (this.pacmanMovementInterval)
            clearInterval(this.pacmanMovementInterval);
          if (this.bugGenerationInterval)
            clearInterval(this.bugGenerationInterval);
        }
      }
    },

    startNextLevel() {
      // Hide the next level button
      this.showNextLevelButton = false;

      // Advance to the next level
      this.level++;

      // Reset game state but keep score
      const currentScore = this.score;
      this.gameOver = false;
      this.gameWon = false;
      this.bugs = [];
      this.sushiItems = [];
      this.walls = [];
      this.powerUps = [];

      // Reset power-up effects and timers
      if (this.activePowerUp && this.activePowerUp.cleanup) {
        this.activePowerUp.cleanup();
      }
      this.activePowerUp = null;
      if (this.powerUpInterval) clearInterval(this.powerUpInterval);
      this.playerInvincible = false;
      this.playerSpeed = 3;
      this.playerFlashing = false;

      // Initialize next level
      this.createLabyrinth();

      // Restore score and add level completion bonus
      this.score = currentScore + 100; // Bonus for completing level

      // Restart game intervals
      this.pacmanMovementInterval = setInterval(
        () => this.updatePacmanPosition(),
        50,
      );
      this.bugGenerationInterval = setInterval(() => this.updateBugs(), 100);
    },

    stopPacmanGame() {
      // Clean up game intervals
      if (this.pacmanMovementInterval)
        clearInterval(this.pacmanMovementInterval);
      if (this.bugGenerationInterval) clearInterval(this.bugGenerationInterval);
      if (this.userControlTimeout) clearTimeout(this.userControlTimeout);

      // Reset user control flag
      this.userControlActive = false;
    },

    togglePacmanGameManually() {
      if (this.showPacmanGame) {
        // If game is already running, stop it
        this.stopPacmanGame();
        if (this.gameHideTimeout) clearTimeout(this.gameHideTimeout);
        this.showPacmanGame = false;
      } else {
        // Otherwise start the game
        this.showPacmanGame = true;
        this.initPacmanGame();
      }
    },

    closePacmanGame() {
      this.stopPacmanGame();
      this.$emit("close"); // Notify parent to close the dialog
    },

    handleKeyDown(event) {
      // The event listener is active only when the component is mounted,
      // so no need to check for dialog visibility here.
      switch (event.key) {
        case "ArrowUp":
          this.pacmanDirection = 270; // up
          this.userControlActive = true;
          // Reset auto control after 3 seconds of inactivity
          this.resetUserControlTimeout();
          break;
        case "ArrowDown":
          this.pacmanDirection = 90; // down
          this.userControlActive = true;
          this.resetUserControlTimeout();
          break;
        case "ArrowLeft":
          this.pacmanDirection = 180; // left
          this.userControlActive = true;
          this.resetUserControlTimeout();
          break;
        case "ArrowRight":
          this.pacmanDirection = 0; // right
          this.userControlActive = true;
          this.resetUserControlTimeout();
          break;
      }
    },

    resetUserControlTimeout() {
      // Clear existing timeout
      if (this.userControlTimeout) {
        clearTimeout(this.userControlTimeout);
      }

      // Set new timeout - after 3 seconds of no input, return to auto mode
      this.userControlTimeout = setTimeout(() => {
        this.userControlActive = false;
      }, 3000);
    },

    restartGame() {
      this.gameOver = false;
      this.gameWon = false;
      this.score = 0;
      this.level = 1;
      this.bugs = [];
      this.sushiItems = [];
      this.walls = [];
      this.powerUps = [];

      // Reset power-up state
      if (this.activePowerUp && this.activePowerUp.cleanup) {
        this.activePowerUp.cleanup();
      }
      this.activePowerUp = null;
      if (this.powerUpInterval) clearInterval(this.powerUpInterval);
      this.playerInvincible = false;
      this.playerSpeed = 3;
      this.playerFlashing = false;

      this.initPacmanGame();
    },
  },
  mounted() {
    this.initPacmanGame();
    window.addEventListener("keydown", this.handleKeyDown);
  },
  beforeUnmount() {
    this.stopPacmanGame();
    if (this.gameHideTimeout) clearTimeout(this.gameHideTimeout);
    if (this.powerUpInterval) clearInterval(this.powerUpInterval);
    window.removeEventListener("keydown", this.handleKeyDown);
  },
};
</script>

<style scoped lang="scss">
.game-container {
  position: relative;
  width: 100%;
  height: 450px;
  background-color: #111;
  border-radius: 8px;
  overflow: hidden;
}
.player {
  position: absolute;
  width: 30px;
  height: 30px;
  transform: rotate(0deg);
  z-index: 10;
  transition: transform 0.2s ease;
}
.player img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 0 4px rgba(255, 255, 255, 0.8));
}
.bug {
  position: absolute;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ff4444;
  transition: transform 0.2s ease;
  filter: drop-shadow(0 0 3px rgba(255, 0, 0, 0.5));
  z-index: 5;
}
.bug i {
  font-size: 24px;
}
.sushi {
  position: absolute;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 5;
}
.sushi img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  filter: drop-shadow(0 0 3px rgba(255, 215, 0, 0.8));
}
.wall {
  position: absolute;
  background-color: #3498db;
  border: 1px solid #2980b9;
  box-shadow: 0 0 8px rgba(52, 152, 219, 0.6);
}
.eaten {
  transform: scale(0);
  opacity: 0;
}
.score {
  font-size: 18px;
  font-weight: bold;
}
.game-instructions {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  color: white;
  font-size: 16px;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 5px 10px;
  border-radius: 5px;
  opacity: 0.7;
  z-index: 20;
}
.game-over-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}
.game-over-text {
  text-align: center;
  color: white;
  padding: 20px;
  background-color: rgba(255, 0, 0, 0.3);
  border: 2px solid #ff4444;
  border-radius: 10px;
}
.game-win-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}
.game-win-text {
  text-align: center;
  color: white;
  padding: 20px;
  background-color: rgba(0, 255, 0, 0.3);
  border: 2px solid #4caf50;
  border-radius: 10px;
}
.game-over {
  animation: shake 0.5s;
}
@keyframes shake {
  0% {
    transform: translate(1px, 1px) rotate(0deg);
  }
  10% {
    transform: translate(-1px, -2px) rotate(-1deg);
  }
  20% {
    transform: translate(-3px, 0px) rotate(1deg);
  }
  30% {
    transform: translate(3px, 2px) rotate(0deg);
  }
  40% {
    transform: translate(1px, -1px) rotate(1deg);
  }
  50% {
    transform: translate(-1px, 2px) rotate(-1deg);
  }
  60% {
    transform: translate(-3px, 1px) rotate(0deg);
  }
  70% {
    transform: translate(3px, 1px) rotate(-1deg);
  }
  80% {
    transform: translate(-1px, -1px) rotate(1deg);
  }
  90% {
    transform: translate(1px, 2px) rotate(0deg);
  }
  100% {
    transform: translate(1px, -2px) rotate(-1deg);
  }
}
.power-up {
  position: absolute;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  z-index: 4;
  border-radius: 50%;
}

.power-up.speed {
  background-color: rgba(255, 215, 0, 0.3);
  box-shadow: 0 0 10px rgba(255, 215, 0, 0.7);
}

.power-up.invincibility {
  background-color: rgba(0, 255, 0, 0.3);
  box-shadow: 0 0 10px rgba(0, 255, 0, 0.7);
}

.power-up.clear {
  background-color: rgba(255, 0, 0, 0.3);
  box-shadow: 0 0 10px rgba(255, 0, 0, 0.7);
}

.active-power-up {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.5);
  padding: 5px 10px;
  border-radius: 5px;
  z-index: 20;
}

.power-up-progress {
  width: 50px;
  height: 8px;
  background-color: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  margin-left: 5px;
  overflow: hidden;
}

.power-up-progress-bar {
  height: 100%;
  background-color: rgba(255, 255, 255, 0.8);
  border-radius: 4px;
}

.player-invincible {
  filter: drop-shadow(0 0 8px rgba(0, 255, 0, 0.8)) brightness(1.5);
}

.player-flashing {
  animation: flash 0.3s infinite alternate;
}

@keyframes flash {
  from {
    opacity: 1;
  }
  to {
    opacity: 0.4;
  }
}

.next-level-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 30;
}

.next-level-text {
  text-align: center;
  color: white;
  padding: 20px;
  background-color: rgba(0, 255, 0, 0.3);
  border: 2px solid #4caf50;
  border-radius: 10px;
}
</style>
