<i18n lang="yaml">
en:
    title: Unauthorized user
    text: Sorry, but your user identity is not associated with any user account in this
          application.

cs:
    title: Nepovolaný uživatel
    text: Je nám líto, ale identita, kterou jste přihlášeni neodpovídá žádnému z účtů v této aplikaci
</i18n>

<template>
    <div class="container">
    <v-card class="middle">
        <v-card-title>{{ $t('title') }}</v-card-title>
        <v-card-text>
            {{ $t('text') }}
        </v-card-text>
    </v-card>
    </div>
</template>
<script>
  export default {
    name: 'InvalidUserPage'
  }
</script>
<style lang="scss" scoped>

    div.container {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 100vh;

        .middle {
            max-width: 30rem;
        }
    }
</style>
