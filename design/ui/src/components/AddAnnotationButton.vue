<i18n>
en:
    add: Add annotation

cs:
    add: Přidat poznámku
</i18n>

<template>
    <span>
        <v-tooltip bottom>
            <template v-slot:activator="{on}">
                <v-btn @click="showDialog = true" v-on="on">
                    <slot>
                        <v-icon small class="mr-2">far fa-sticky-note</v-icon>
                        {{ $t('add') }}
                    </slot>
                </v-btn>
            </template>
            {{ $t('add') }}
        </v-tooltip>
        <v-dialog
                v-model="showDialog"
        >
            <v-card>
                <v-card-title v-text="$t('add')"></v-card-title>
                <v-card-text>
                    <AnnotationCreateModifyWidget
                            :platform="platform"
                            @saved="annotationSaved"
                            @cancel="cancelEdit"
                            @deleted="annotationSaved"
                    />
                </v-card-text>
            </v-card>
        </v-dialog>
    </span>
</template>
<script>
  import AnnotationCreateModifyWidget from './AnnotationCreateModifyWidget'

  export default {
    name: 'AddAnnotationButton',
    components: {AnnotationCreateModifyWidget},
    props: {
      platform: {},
    },
    data () {
      return {
        showDialog: false,
      }
    },
    methods: {
      cancelEdit () {
        this.showDialog = false
      },
      annotationSaved () {
        this.showDialog = false
        this.$emit('update')
      }
    }
  }
</script>
