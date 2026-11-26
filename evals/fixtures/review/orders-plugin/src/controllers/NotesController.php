<?php

namespace acme\orders\controllers;

use acme\orders\Plugin;
use acme\orders\records\NoteRecord;
use craft\web\Controller;
use yii\web\NotFoundHttpException;
use yii\web\Response;

/**
 * Saves notes on orders from the control panel.
 *
 * @author Acme
 * @since 1.0.0
 */
class NotesController extends Controller
{
    // Public Methods
    // =========================================================================

    /**
     * Saves a note.
     *
     * @return Response
     * @throws NotFoundHttpException
     * @author Acme
     */
    public function actionSave(): Response
    {
        $this->requirePostRequest();
        $noteId = $this->request->getRequiredBodyParam('noteId');
        $this->requirePermission(Plugin::PERMISSION_MANAGE_NOTES);

        $note = NoteRecord::findOne($noteId);
        if (!$note) {
            throw new NotFoundHttpException('Note not found');
        }

        $note->text = $this->request->getRequiredBodyParam('text');
        if (!$note->save()) {
            return $this->asFailure('Couldn’t save the note.');
        }

        return $this->asSuccess('Note saved.');
    }
}
