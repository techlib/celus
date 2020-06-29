<i18n lang="yaml">
en:
    step1: Hello
    step1_text: Hello, it looks like you are new to Celus and there are no data in your account.
        Let me help you with setting up your first SUSHI download - it will give you some data
        to play with and at the same time teach you how Celus works.
    step2: SUSHI intro
    step2_text: Celus works by obtaining usage statistics data from your vendor's server using
        the so called SUSHI protocol. In order to get the data, you have to know the address
        of the server and a few identification information.
</i18n>

<template>
    <v-stepper v-model="step">
        <v-stepper-header>
            <v-stepper-step :step="1" :complete="step > 1" editable>
                {{ $t('step1') }}
            </v-stepper-step>
            <v-stepper-step :step="2" :complete="step > 2" editable>
                {{ $t('step2') }}
            </v-stepper-step>
            <v-stepper-step :step="3" :complete="step > 3" editable>
                {{ $t('step3') }}
            </v-stepper-step>
        </v-stepper-header>

        <v-stepper-items>
            <v-stepper-content :step="1">
                <div>{{ $t('step1_text') }}</div>
                <div>
                    <v-btn @click="step++">{{ $t('continue') }}</v-btn>
                </div>
            </v-stepper-content>

            <v-stepper-content :step="2">
                <div>{{ $t('step2_text') }}</div>
            </v-stepper-content>

            <v-stepper-content :step="3">
                <div>{{ $t('step3_text') }}</div>
            </v-stepper-content>
        </v-stepper-items>
    </v-stepper>
</template>

<script>
  export default {
    name: 'FirstSushiHelpWidget',

    data () {
      return {
        step: 1,
      }
    }
  }
</script>

<style scoped>

</style>
